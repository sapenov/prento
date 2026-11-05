#include "prento/net.hpp"
#include "prento/threads.hpp"
#include "prento/timing.hpp"
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

namespace prento {
int sink(const Args& args) {
    auto rate=args.real("bytes-per-sec",1048576);
    auto factor=args.real("slow-factor",10);
    if(rate<=0 || factor<1)throw std::invalid_argument("invalid sink rate/factor");
    int port=bounded_int(args.num("port",9001),"port",1,65535);
    auto maxbatch=args.num("max-batch-bytes",16777216);
    if(!maxbatch || maxbatch>1073741824)throw std::invalid_argument("invalid max batch");
    auto listener=listen_on(port,args.str("bind","127.0.0.1"));
    auto start=Clock::now();
    double slowstart=args.real("slow-start-ms",1000),slowms=args.real("slow-ms",0);
    double outstart=args.real("outage-start-ms",1000),outms=args.real("outage-ms",0);
    if(slowstart<0 || slowms<0 || outstart<0 || outms<0)throw std::invalid_argument("negative interval");
    std::mutex service,peers_mutex;
    std::vector<int> peers;
    ReapingThreads sessions;
    auto pause=[&](double milliseconds) {
        auto duration=std::chrono::duration_cast<Clock::duration>(std::chrono::duration<double,std::milli>(milliseconds));
        pause_for(duration,[]{return Clock::now();},
                  [](Clock::duration step){std::this_thread::sleep_for(step);},
                  []{return stopping.load();});
    };
    std::cout<<"sink listening "<<port<<std::endl;
    while(!stopping) {
        sessions.reap();
        int fd=accept_ready(listener.get());if(fd<0)continue;
        {std::lock_guard lock(peers_mutex);if(peers.size()>=128){::close(fd);continue;}peers.push_back(fd);}
        sessions.launch([&,fd] {
            Socket client(fd);
            try {
                while(!stopping) {
                    auto h=next_header(fd,1000);
                    if(h.type!=Announce || h.credit || !h.bytes || h.bytes>maxbatch)throw std::runtime_error("invalid sink frame");
                    std::string body(h.bytes,'\0');io(fd,body.data(),body.size(),false,1000);
                    if(checksum(body)!=h.hash)throw std::runtime_error("sink checksum mismatch");
                    {
                        std::lock_guard lock(service);
                        auto elapsed=std::chrono::duration<double,std::milli>(Clock::now()-start).count();
                        if(elapsed>=outstart && elapsed<outstart+outms)pause(outstart+outms-elapsed);
                        elapsed=std::chrono::duration<double,std::milli>(Clock::now()-start).count();
                        auto multiplier=elapsed>=slowstart && elapsed<slowstart+slowms?factor:1;
                        pause(1000.0*h.bytes/rate*multiplier);
                        if(stopping)break;
                        h.type=Ack;send_header(fd,h,1000);
                    }
                }
            }catch(const std::exception&){}
            {std::lock_guard lock(peers_mutex);std::erase(peers,fd);}
        });
    }
    {std::lock_guard lock(peers_mutex);for(int fd:peers)::shutdown(fd,SHUT_RDWR);}
    sessions.join_all();
    return 0;
}
}
