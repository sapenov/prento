FROM ubuntu:24.04 AS build
RUN apt-get update && apt-get install -y --no-install-recommends \
    g++ cmake ninja-build ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY CMakeLists.txt ./
COPY include ./include
COPY src ./src
COPY tests/core_test.cpp ./tests/core_test.cpp
RUN cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release \
    && cmake --build build && ctest --test-dir build --output-on-failure

FROM ubuntu:24.04 AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libstdc++6 libgcc-s1 && rm -rf /var/lib/apt/lists/* \
    && mkdir /results && chown 10001:10001 /results
COPY --from=build /src/build/fanin /usr/local/bin/fanin
USER 10001:10001
WORKDIR /tmp
EXPOSE 9000 9001 9090
ENTRYPOINT ["/usr/local/bin/fanin"]
CMD ["--help"]

# Optional benchmark runner: same application plus stdlib-only orchestration.
FROM runtime AS bench
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 && rm -rf /var/lib/apt/lists/*
COPY scripts /lab/scripts
RUN mkdir -p /results && chown 10001:10001 /results
USER 10001:10001
ENTRYPOINT ["python3", "/lab/scripts/bench.py", "--binary", "/usr/local/bin/fanin"]
CMD ["--output", "/results/run"]

# QA toolchain: native and sanitizer tests without host compiler dependencies.
FROM build AS qa
RUN apt-get update && apt-get install -y --no-install-recommends \
    make python3 util-linux && rm -rf /var/lib/apt/lists/*
COPY Makefile ./
COPY tests ./tests
COPY scripts ./scripts
CMD ["make", "test"]
