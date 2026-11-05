#pragma once
#include <cstdint>
#include <optional>
#include <stdexcept>
#include <string_view>
#include <vector>

namespace prento {
struct Item { std::uint64_t id; std::size_t bytes; bool critical; };

class Budget {
    std::size_t limit_, used_=0, peak_=0;
public:
    explicit Budget(std::size_t limit):limit_(limit) {
        if (!limit) throw std::invalid_argument("buffer must be positive");
    }
    bool reserve(std::size_t bytes) {
        if (!bytes || bytes>limit_-used_) return false;
        used_+=bytes; if (used_>peak_) peak_=used_; return true;
    }
    void release(std::size_t bytes) {
        if (bytes>used_) throw std::logic_error("reservation underflow");
        used_-=bytes;
    }
    std::size_t available() const { return limit_-used_; }
    std::size_t used() const { return used_; }
    std::size_t peak() const { return peak_; }
    std::size_t limit() const { return limit_; }
};

// Selection is FIFO within class; periodically offer bulk a turn.
// Skip entries that cannot fit, rather than violating the reservation cap.
class Selector {
    bool priority_;
    unsigned quota_, streak_=0;
public:
    Selector(bool priority,unsigned quota):priority_(priority),quota_(quota) {
        if (!quota) throw std::invalid_argument("priority quota must be positive");
    }
    std::optional<std::size_t> choose(const std::vector<Item>& items,std::size_t available) const {
        std::optional<std::size_t> first,critical,bulk;
        for(std::size_t i=0;i<items.size();++i) {
            if(items[i].bytes>available) continue;
            if(!first) first=i;
            if(items[i].critical && !critical) critical=i;
            if(!items[i].critical && !bulk) bulk=i;
        }
        if(!priority_) return first;
        if(streak_>=quota_ && bulk) return bulk;
        return critical ? critical : bulk;
    }
    void served(bool critical) { if(critical) { if(streak_<quota_) ++streak_; } else streak_=0; }
};
inline std::uint32_t checksum(std::string_view bytes) {
    std::uint32_t hash=2166136261U;
    for(unsigned char c:bytes) { hash^=c; hash*=16777619U; }
    return hash;
}
}
