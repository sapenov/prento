#pragma once
#include <atomic>
#include <memory>
#include <thread>
#include <utility>
#include <vector>

namespace fanin {
// Main-thread-owned container. Reclaim completed thread handles between accepts.
class ReapingThreads {
    struct Worker { std::shared_ptr<std::atomic_bool> done; std::thread thread; };
    std::vector<Worker> workers_;
public:
    ~ReapingThreads() { join_all(); }
    template<class F> void launch(F&& function) {
        if(workers_.size()==workers_.capacity())workers_.reserve(workers_.size()*2+1);
        auto done=std::make_shared<std::atomic_bool>(false);
        std::thread thread([done,fn=std::forward<F>(function)]() mutable {
            fn();done->store(true,std::memory_order_release);
        });
        workers_.push_back({done,std::move(thread)});
    }
    void reap() {
        for(auto it=workers_.begin();it!=workers_.end();) {
            if(it->done->load(std::memory_order_acquire)) {
                it->thread.join();it=workers_.erase(it);
            }else ++it;
        }
    }
    void join_all() { for(auto& w:workers_)if(w.thread.joinable())w.thread.join();workers_.clear(); }
    std::size_t size() const { return workers_.size(); }
};
}
