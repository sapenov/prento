#pragma once
#include <algorithm>
#include <chrono>

namespace prento {
// Clock and sleeper injection makes service timing deterministic in unit tests.
template<class Duration,class Now,class Sleep,class Stop>
void pause_for(Duration duration,Now now,Sleep sleep,Stop stopped) {
    const auto end=now()+duration;
    const auto maximum=std::chrono::duration_cast<typename decltype(end)::duration>(std::chrono::milliseconds(1));
    while(!stopped()) {
        const auto current=now();
        if(current>=end)break;
        sleep(std::min(end-current,maximum));
    }
}
}
