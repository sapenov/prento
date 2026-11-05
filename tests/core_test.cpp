#include "prento/core.hpp"
#include "prento/threads.hpp"
#include "prento/timing.hpp"
#include <atomic>
#include <iostream>
#include <stdexcept>

void check(bool ok, const char* msg) { if (!ok) throw std::runtime_error(msg); }
int main() {
    using namespace prento;
    try {
        Budget b(100);
        check(b.reserve(70), "initial reservation");
        check(!b.reserve(31), "must enforce global byte cap");
        check(b.used()==70, "failed reservation changes nothing");
        b.release(70);
        check(b.used()==0 && b.peak()==70, "release and peak");
        bool threw=false;
        try { b.release(1); } catch (const std::logic_error&) { threw=true; }
        check(threw, "underflow must fail");
        check(!b.reserve(101), "oversize rejected");
        std::vector<Item> q{{1,64,false},{2,16,true},{3,32,true},{4,16,false}};
        Selector fifo(false,4);
        check(fifo.choose(q,100).value()==0, "fifo arrival order");
        Selector priority(true,2);
        check(priority.choose(q,100).value()==1, "critical first");
        priority.served(true);
        check(priority.choose(q,100).value()==1, "critical within quota");
        priority.served(true);
        check(priority.choose(q,100).value()==0, "bulk fairness opportunity");
        check(!fifo.choose(q,8).has_value(), "no reservation fits");
        check(fifo.choose(q,20).value()==1, "fit without exceeding available bytes");
        check(checksum(std::string("abc"))==440920331U, "FNV-1a known vector");
        ReapingThreads pool;
        std::atomic<unsigned> finished=0;
        for(unsigned i=0;i<100;++i) {
            pool.reap();
            pool.launch([&]{++finished;});
        }
        pool.join_all();
        check(finished==100 && pool.size()==0, "completed sessions are joined and reclaimed");
        using TestClock=std::chrono::steady_clock;
        auto clock=TestClock::time_point{};
        std::vector<TestClock::duration> sleeps;
        auto now=[&]{return clock;};
        auto sleep=[&](TestClock::duration value){sleeps.push_back(value);clock+=value;};
        pause_for(std::chrono::microseconds(60),now,sleep,[]{return false;});
        check(sleeps.size()==1 && sleeps[0]==std::chrono::microseconds(60), "submillisecond pause must not round up to 1ms");
        sleeps.clear();clock=TestClock::time_point{};
        pause_for(std::chrono::microseconds(2500),now,sleep,[]{return false;});
        check(sleeps.size()==3 && sleeps[2]==std::chrono::microseconds(500), "final sleep uses remaining duration");
        sleeps.clear();
        pause_for(std::chrono::milliseconds(10),now,sleep,[]{return true;});
        check(sleeps.empty(), "stopped pause never sleeps");
        pause_for(TestClock::duration::zero(),now,sleep,[]{return false;});
        check(sleeps.empty(), "zero duration never sleeps");
        std::cout << "core: 18 checks passed\n";
    } catch (const std::exception& e) { std::cerr<<e.what()<<'\n'; return 1; }
}
