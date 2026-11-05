CXX ?= g++
CPPFLAGS := -Iinclude
CXXFLAGS ?= -std=c++20 -O2 -g -Wall -Wextra -Wpedantic -Werror -pthread
SOURCES := src/main.cpp src/collector.cpp src/producer.cpp src/sink.cpp

.PHONY: all test unit integration bench report clean sanitize tsan qa-bundle
all: build/prento
build:
	mkdir -p build
build/prento: $(SOURCES) $(wildcard include/prento/*.hpp) | build
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(SOURCES) -o $@
build/core-test: tests/core_test.cpp $(wildcard include/prento/*.hpp) | build
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $< -o $@
unit: build/core-test
	./build/core-test
integration: build/prento
	python3 -m unittest discover -s tests -p 'test_*.py' -v
test: unit integration
bench: build/prento
	python3 scripts/bench.py --output results/latest
report:
	python3 scripts/report.py results/latest
sanitize:
	mkdir -p build
	$(CXX) $(CPPFLAGS) -std=c++20 -O1 -g -Wall -Wextra -Wpedantic -Werror -pthread -fsanitize=address,undefined -fno-omit-frame-pointer -fno-pie -no-pie tests/core_test.cpp -o build/core-test-asan
	./build/core-test-asan
	$(CXX) $(CPPFLAGS) -std=c++20 -O1 -g -Wall -Wextra -Wpedantic -Werror -pthread -fsanitize=address,undefined -fno-omit-frame-pointer -fno-pie -no-pie $(SOURCES) -o build/prento-asan
	PRENTO_BINARY=$(CURDIR)/build/prento-asan python3 -m unittest discover -s tests -p 'test_*.py' -v
tsan:
	mkdir -p build
	$(CXX) $(CPPFLAGS) -std=c++20 -O1 -g -Wall -Wextra -Wpedantic -Werror -pthread -fsanitize=thread -fno-omit-frame-pointer -fno-pie -no-pie tests/core_test.cpp -o build/core-test-tsan
	./build/core-test-tsan
	$(CXX) $(CPPFLAGS) -std=c++20 -O1 -g -Wall -Wextra -Wpedantic -Werror -pthread -fsanitize=thread -fno-omit-frame-pointer -fno-pie -no-pie $(SOURCES) -o build/prento-tsan
	PRENTO_BINARY=$(CURDIR)/build/prento-tsan python3 -m unittest discover -s tests -p 'test_*.py' -v
qa-bundle:
	python3 scripts/bundle.py --results results/2026-11-04-qa --results results/2026-11-04-container --output dist/prento-qa.zip
clean:
	rm -rf build
