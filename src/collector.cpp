#include "fanin/net.hpp"
#include "fanin/threads.hpp"
#include <condition_variable>
#include <deque>
#include <iostream>
#include <mutex>
#include <sstream>
#include <thread>
#include <vector>

namespace fanin {
namespace {
struct Gate {
    std::mutex mutex;
    std::condition_variable changed;
    Budget budget;
    Selector admission,service;
    std::vector<Item> waiting,ready;
    std::uint64_t ticket=0,completed=0,failed=0,admitted=0,admitted_bytes=0;
    bool busy=false,closed=false;
    explicit Gate(std::size_t bytes,bool priority,unsigned quota):budget(bytes),admission(priority,quota),service(priority,quota){}
    bool acquire(Item item,int timeout) {
        std::unique_lock lock(mutex);
        waiting.push_back(item);
        auto deadline=Clock::now()+std::chrono::milliseconds(timeout);
        auto selected=[&]{ auto i=admission.choose(waiting,budget.available()); return i && waiting[*i].id==item.id; };
        changed.wait_until(lock,deadline,[&]{return closed || selected();});
        if(closed || !selected()) {
            std::erase_if(waiting,[&](auto& i){return i.id==item.id;}); changed.notify_all(); return false;
        }
        std::erase_if(waiting,[&](auto& i){return i.id==item.id;});
        if(!budget.reserve(item.bytes)) throw std::logic_error("admission exceeded byte budget");
        admission.served(item.critical); ++admitted;admitted_bytes+=item.bytes;changed.notify_all();return true;
    }
    bool begin(Item item,int timeout) {
        std::unique_lock lock(mutex);ready.push_back(item);
        auto selected=[&]{ auto i=service.choose(ready,budget.limit()); return !busy && i && ready[*i].id==item.id; };
        changed.wait_for(lock,std::chrono::milliseconds(timeout),[&]{return closed || selected();});
        bool ok=!closed && selected();
        std::erase_if(ready,[&](auto& i){return i.id==item.id;});
        if(ok){busy=true;service.served(item.critical);} changed.notify_all();return ok;
    }
    void finish(Item item,bool success,bool started) {
        std::lock_guard lock(mutex);budget.release(item.bytes);
        if(started) busy=false;
        if(success)++completed;else ++failed;
        changed.notify_all();
    }
    std::string metrics() {
        std::lock_guard lock(mutex);
        std::ostringstream out;
        out<<"fanin_reserved_bytes "<<budget.used()<<"\nfanin_reserved_peak_bytes "<<budget.peak()
           <<"\nfanin_buffer_limit_bytes "<<budget.limit()<<"\nfanin_admitted_total "<<admitted
           <<"\nfanin_admitted_bytes_total "<<admitted_bytes
           <<"\nfanin_completed_total "<<completed<<"\nfanin_failed_total "<<failed
           <<"\nfanin_waiting_announcements "<<waiting.size()<<"\nfanin_ready_batches "<<ready.size()<<'\n';
        return out.str();
    }
};
}
int collector(const Args& args) {
    auto buffer=args.num("buffer-bytes",1048576), maxbatch=args.num("max-batch-bytes",65536);
    if(!buffer || !maxbatch || maxbatch>buffer || buffer>1073741824) throw std::invalid_argument("invalid buffer/batch sizes");
    auto mode=args.str("admission","push"),policy=args.str("policy","fifo");
    if(mode!="push" && mode!="credit") throw std::invalid_argument("admission must be push or credit");
    if(policy!="fifo" && policy!="priority") throw std::invalid_argument("policy must be fifo or priority");
    int timeout=bounded_int(args.num("timeout-ms",5000),"timeout",1,60000);
    int maxclients=bounded_int(args.num("max-clients",128),"max-clients",1,1024);
    auto port=bounded_int(args.num("port",9000),"port",1,65535);
    auto mp=bounded_int(args.num("metrics-port",9090),"metrics-port",1,65535);
    auto bind=args.str("bind","127.0.0.1");
    auto listener=listen_on(port,bind),health=listen_on(mp,bind);
    Gate gate(buffer,policy=="priority",bounded_int(args.num("priority-quota",4),"priority-quota",1,1000));
    std::mutex peers_mutex,backend_mutex;
    std::vector<int> peers;
    ReapingThreads sessions;
    Socket backend;
    auto target=args.str("sink","127.0.0.1:9001");
    std::thread monitor([&] {
        while(!stopping) {
            Socket client(accept_ready(health.get()));if(!client)continue;
            try {
                char request[1024]{};
                pollfd p{client.get(),POLLIN,0};
                if(::poll(&p,1,200)<=0)continue;
                auto n=::recv(client.get(),request,sizeof(request)-1,MSG_DONTWAIT);
                if(n<=0)continue;
                std::string path(request,static_cast<std::size_t>(n));
                bool metrics=path.starts_with("GET /metrics ");
                bool valid=metrics || path.starts_with("GET /readyz ") || path.starts_with("GET /livez ");
                auto body=metrics?gate.metrics():(valid?"ok\n":"not found\n");
                auto response=std::string(valid?"HTTP/1.1 200 OK\r\n":"HTTP/1.1 404 Not Found\r\n")+
                    "Content-Type: text/plain\r\nConnection: close\r\nContent-Length: "+std::to_string(body.size())+"\r\n\r\n"+body;
                send_bytes(client.get(),response,500);
            }catch(const std::exception&){}
        }
    });
    std::cout<<"collector listening "<<port<<" "<<mode<<"/"<<policy<<std::endl;
    while(!stopping) {
        sessions.reap();
        int fd=accept_ready(listener.get()); if(fd<0)continue;
        { std::lock_guard lock(peers_mutex);
          if(peers.size()>=static_cast<std::size_t>(maxclients)){::close(fd);continue;} peers.push_back(fd); }
        sessions.launch([&,fd] {
            Socket client(fd);
            try {
                while(!stopping) {
                    auto h=next_header(fd,timeout);
                    if(h.type!=Announce || !h.bytes || h.bytes>maxbatch || h.credit!=(mode=="credit")) {
                        h.type=Reject;send_header(fd,h,timeout);break;
                    }
                    Item item;
                    {std::lock_guard lock(gate.mutex);item={++gate.ticket,h.bytes,h.critical};}
                    if(!gate.acquire(item,timeout)){h.type=Reject;send_header(fd,h,timeout);break;}
                    bool started=false,success=false;
                    try {
                        if(h.credit){h.type=Grant;send_header(fd,h,timeout);h.type=Announce;}
                        std::string payload(h.bytes,'\0');io(fd,payload.data(),payload.size(),false,timeout);
                        if(checksum(payload)!=h.hash)throw std::runtime_error("payload checksum mismatch");
                        started=gate.begin(item,timeout);
                        if(started) {
                            std::lock_guard lock(backend_mutex);
                            try {
                                if(!backend)backend=connect_to(target,timeout);
                                auto outgoing=h;outgoing.credit=false;
                                send_header(backend.get(),outgoing,timeout);send_bytes(backend.get(),payload,timeout);
                                auto reply=read_header(backend.get(),timeout);
                                success=reply.type==Ack && reply.id==h.id;
                                if(!success) backend=Socket();
                            } catch(const std::exception&){backend=Socket();}
                        }
                    }catch(const std::exception&){}
                    gate.finish(item,success,started);
                    h.type=success?Ack:Reject;send_header(fd,h,timeout);
                    if(!success)break;
                }
            }catch(const std::exception&){}
            {std::lock_guard lock(peers_mutex);std::erase(peers,fd);}
        });
    }
    {std::lock_guard lock(gate.mutex);gate.closed=true;gate.changed.notify_all();}
    {std::lock_guard lock(peers_mutex);for(int fd:peers)::shutdown(fd,SHUT_RDWR);}
    monitor.join();sessions.join_all();
    std::cout<<gate.metrics();return 0;
}
}
