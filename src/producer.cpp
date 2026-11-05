#include "prento/net.hpp"
#include <condition_variable>
#include <deque>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <random>
#include <thread>
#include <vector>

namespace prento {
namespace {
struct Work { Header header; };
struct Queue {
    std::mutex mutex;
    std::condition_variable changed;
    std::deque<Work> work;
    bool done=false;
    std::uint64_t bytes=0,peakbytes=0;
};
}
int producer(const Args& args) {
    double rate=args.real("rate",200),fraction=args.real("critical-fraction",.05);
    if(rate<=0 || rate>1000000 || fraction<0 || fraction>1)throw std::invalid_argument("invalid rate/fraction");
    auto duration=bounded_int(args.num("duration-ms",3000),"duration-ms",1,3600000);
    auto count=bounded_int(args.num("producers",16),"producers",1,256);
    auto queuecap=bounded_int(args.num("queue-items",128),"queue-items",1,100000);
    auto timeout=bounded_int(args.num("timeout-ms",5000),"timeout-ms",1,60000);
    auto criticalbytes=bounded_int(args.num("critical-bytes",256),"critical-bytes",1,16777216);
    auto bulkbytes=bounded_int(args.num("bulk-bytes",32768),"bulk-bytes",1,16777216);
    auto mode=args.str("admission","push");
    if(mode!="push" && mode!="credit")throw std::invalid_argument("admission must be push or credit");
    auto burst=args.real("burst-factor",1);
    if(burst<1 || burst>100)throw std::invalid_argument("invalid burst-factor");
    auto target=args.str("target","127.0.0.1:9000");
    auto seed=args.num("seed",42);
    auto delay=bounded_int(args.num("start-delay-ms",100),"start-delay-ms",0,60000);
    std::ofstream output(args.str("output","outcomes.csv"));
    if(!output)throw std::runtime_error("cannot open output CSV");
    output<<"id,producer,class,bytes,intended_ns,send_ns,end_ns,latency_ms,producer_wait_ms,status\n";
    std::mutex outmutex;
    std::atomic<std::uint64_t> completed=0,failed=0,dropped=0;
    std::vector<Queue> queues(count);
    auto record=[&](const Header& h,int worker,std::uint64_t sent,const char* status) {
        auto end=now_ns();
        std::lock_guard lock(outmutex);
        output<<h.id<<','<<worker<<','<<(h.critical?"critical":"bulk")<<','<<h.bytes<<','
              <<h.intended_ns<<','<<sent<<','<<end<<','<<std::fixed<<std::setprecision(6)
              <<(end-h.intended_ns)/1e6<<','<<(sent? (sent-h.intended_ns)/1e6:0)<<','<<status<<'\n';
    };
    std::vector<std::thread> workers;
    for(int worker=0;worker<count;++worker)workers.emplace_back([&,worker] {
        Socket connection;
        auto& q=queues[worker];
        while(true) {
            Header h;
            {
                std::unique_lock lock(q.mutex);
                q.changed.wait(lock,[&]{return q.done || !q.work.empty();});
                if(q.work.empty())break;
                h=q.work.front().header;q.work.pop_front();q.bytes-=h.bytes;
            }
            std::uint64_t sent=0;
            try {
                if(stopping)throw std::runtime_error("producer stopping");
                std::string body(h.bytes,static_cast<char>(h.id%251));
                h.hash=checksum(body);
                if(!connection)connection=connect_to(target,timeout);
                sent=now_ns();send_header(connection.get(),h,timeout);
                if(h.credit) {
                    auto grant=read_header(connection.get(),timeout);
                    if(grant.type!=Grant || grant.id!=h.id || grant.bytes!=h.bytes)throw std::runtime_error("invalid grant/rejection");
                }
                send_bytes(connection.get(),body,timeout);
                auto ack=read_header(connection.get(),timeout);
                if(ack.type!=Ack || ack.id!=h.id)throw std::runtime_error("batch not acknowledged");
                ++completed;record(h,worker,sent,"completed");
            }catch(const std::exception&) {
                connection=Socket();++failed;record(h,worker,sent,"failed_unknown");
            }
        }
    });
    std::mt19937_64 random(seed);
    // Integer threshold avoids distribution implementation differences between standard libraries.
    auto start=now_ns()+static_cast<std::uint64_t>(delay)*1000000;
    std::uint64_t offset=0,generated=0;
    while(offset<static_cast<std::uint64_t>(duration)*1000000 && !stopping) {
        auto intended=start+offset;
        while(!stopping) {
            auto current=now_ns();
            if(current>=intended)break;
            std::this_thread::sleep_for(std::chrono::nanoseconds(std::min<std::uint64_t>(intended-current,10000000)));
        }
        if(stopping)break;
        bool critical=(random()%1000000)<static_cast<std::uint64_t>(fraction*1000000);
        Header h{Announce,critical,mode=="credit",++generated,
                 static_cast<std::uint32_t>(critical?criticalbytes:bulkbytes),0,intended};
        int worker=static_cast<int>((generated-1)%count);
        auto& q=queues[worker];bool rejected=false;
        {
            std::lock_guard lock(q.mutex);
            if(q.work.size()>=static_cast<std::size_t>(queuecap))rejected=true;
            else {q.work.push_back({h});q.bytes+=h.bytes;q.peakbytes=std::max(q.peakbytes,q.bytes);q.changed.notify_one();}
        }
        if(rejected){++dropped;record(h,worker,0,"producer_drop");}
        double elapsed_ms=offset/1e6;
        auto multiplier=elapsed_ms>=duration*.3 && elapsed_ms<duration*.5?burst:1;
        offset+=static_cast<std::uint64_t>(1000000000.0/(rate*multiplier));
    }
    for(auto& q:queues){std::lock_guard lock(q.mutex);q.done=true;q.changed.notify_all();}
    for(auto& w:workers)w.join();
    output.flush();if(!output)throw std::runtime_error("failed writing output CSV");
    std::uint64_t logical_peak_sum=0;for(auto& q:queues)logical_peak_sum+=q.peakbytes;
    std::cout<<"{\"generated\":"<<generated<<",\"completed\":"<<completed.load()
             <<",\"failed_unknown\":"<<failed.load()<<",\"producer_drop\":"<<dropped.load()
             <<",\"sum_per_producer_peak_queued_bytes\":"<<logical_peak_sum<<"}\n";
    return generated==completed+failed+dropped?0:2;
}
}
