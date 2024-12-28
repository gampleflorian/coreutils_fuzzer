#
# This Dockerfile for AFLplusplus uses Ubuntu 22.04 jammy and
# installs LLVM 14 for afl-clang-lto support.
#
# GCC 11 is used instead of 12 because genhtml for afl-cov doesn't like it.
#

FROM ubuntu:22.04 AS coreutils_argenv_fuzz

### Comment out to enable these features
# Only available on specific ARM64 boards
ENV NO_CORESIGHT=1
# Possible but unlikely in a docker container
ENV NO_NYX=1

### Only change these if you know what you are doing:
# LLVM 15 does not look good so we stay at 14 to still have LTO
ENV LLVM_VERSION=14
# GCC 12 is producing compile errors for some targets so we stay at GCC 11
ENV GCC_VERSION=11

### No changes beyond the point unless you know what you are doing :)

ARG DEBIAN_FRONTEND=noninteractive

ENV NO_ARCH_OPT=1
ENV IS_DOCKER=1

RUN apt-get update && apt-get full-upgrade -y && \
    apt-get install -y --no-install-recommends wget ca-certificates apt-utils && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /etc/apt/keyrings/
RUN mkdir -p /etc/apt/sources.list.d/
RUN echo "deb [signed-by=/etc/apt/keyrings/llvm-snapshot.gpg.key] http://apt.llvm.org/jammy/ llvm-toolchain-jammy-${LLVM_VERSION} main" > /etc/apt/sources.list.d/llvm.list && \
    echo "deb-src [signed-by=/etc/apt/keyrings/llvm-snapshot.gpg.key] http://apt.llvm.org/jammy/ llvm-toolchain-jammy-${LLVM_VERSION} main" >> /etc/apt/sources.list.d/llvm.list && \
    wget -qO llvm-snapshot.gpg.key https://apt.llvm.org/llvm-snapshot.gpg.key && \
    cp llvm-snapshot.gpg.key /etc/apt/keyrings/llvm-snapshot.gpg.key && \
    chmod a+r /etc/apt/keyrings/llvm-snapshot.gpg.key

RUN cat /etc/apt/sources.list.d/llvm.list

RUN apt-get update && \
    apt-get -y install --no-install-recommends \
    make cmake automake meson ninja-build bison flex \
    git xz-utils bzip2 wget jupp nano bash-completion less vim joe ssh psmisc \
    python3 python3-dev python3-setuptools python-is-python3 \
    libtool libtool-bin libglib2.0-dev \
    apt-transport-https gnupg dialog \
    gnuplot-nox libpixman-1-dev uuid-dev \
    autopoint gettext gperf autoconf automake bison git help2man m4 perl texinfo patch rsync \
    gcc-${GCC_VERSION} g++-${GCC_VERSION} gcc-${GCC_VERSION}-plugin-dev gdb lcov \
    clang-${LLVM_VERSION} clang-tools-${LLVM_VERSION} libc++1-${LLVM_VERSION} \
    libc++-${LLVM_VERSION}-dev libc++abi1-${LLVM_VERSION} libc++abi-${LLVM_VERSION}-dev \
    libclang1-${LLVM_VERSION} libclang-${LLVM_VERSION}-dev \
    libclang-common-${LLVM_VERSION}-dev libclang-cpp${LLVM_VERSION} \
    libclang-cpp${LLVM_VERSION}-dev liblld-${LLVM_VERSION} \
    liblld-${LLVM_VERSION}-dev liblldb-${LLVM_VERSION} liblldb-${LLVM_VERSION}-dev \
    libllvm${LLVM_VERSION} libomp-${LLVM_VERSION}-dev libomp5-${LLVM_VERSION} \
    lld-${LLVM_VERSION} lldb-${LLVM_VERSION} llvm-${LLVM_VERSION} \
    llvm-${LLVM_VERSION}-dev llvm-${LLVM_VERSION}-runtime llvm-${LLVM_VERSION}-tools \
    $([ "$(dpkg --print-architecture)" = "amd64" ] && echo gcc-${GCC_VERSION}-multilib gcc-multilib) \
    $([ "$(dpkg --print-architecture)" = "arm64" ] && echo libcapstone-dev) && \
    rm -rf /var/lib/apt/lists/*
    # gcc-multilib is only used for -m32 support on x86
    # libcapstone-dev is used for coresight_mode on arm64

RUN update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-${GCC_VERSION} 0 && \
    update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-${GCC_VERSION} 0 && \
    update-alternatives --install /usr/bin/clang clang /usr/bin/clang-${LLVM_VERSION} 0 && \
    update-alternatives --install /usr/bin/clang++ clang++ /usr/bin/clang++-${LLVM_VERSION} 0

RUN wget -qO- https://sh.rustup.rs | CARGO_HOME=/etc/cargo sh -s -- -y -q --no-modify-path
ENV PATH=$PATH:/etc/cargo/bin

ENV LLVM_CONFIG=llvm-config-${LLVM_VERSION}
ENV AFL_SKIP_CPUFREQ=1
ENV AFL_TRY_AFFINITY=1
ENV AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1

RUN git clone --depth=1 https://github.com/vanhauser-thc/afl-cov && \
    (cd afl-cov && make install) && rm -rf afl-cov

RUN echo "new"
RUN git clone https://github.com/file-citas/AFLplusplus_argvenv.git /AFLplusplus

ARG CC=gcc-$GCC_VERSION
ARG CXX=g++-$GCC_VERSION

# Used in CI to prevent a 'make clean' which would remove the binaries to be tested
ARG TEST_BUILD
WORKDIR /AFLplusplus

RUN sed -i.bak 's/^	-/	/g' GNUmakefile && \
    make clean && make all && \
    ([ "${TEST_BUILD}" ] || (make install && make clean)) && \
    mv GNUmakefile.bak GNUmakefile

WORKDIR /AFLplusplus/utils/argv_fuzzing
RUN make && make install

RUN git clone https://github.com/file-citas/coreutils_fuzz_argvenv.git /coreutils_afpp_src
RUN mkdir /coreutils_afpp
RUN mkdir /coreutils_afpp_laf
RUN mkdir /coreutils_afpp_rq
RUN mkdir /coreutils_afpp_src/obj
RUN mkdir /coreutils_afpp_src/obj-laf
RUN mkdir /coreutils_afpp_src/obj-rq
WORKDIR /coreutils_afpp_src/
RUN ./bootstrap

WORKDIR /coreutils_afpp_src/obj
RUN CC=afl-clang-lto CXX=afl-clang-lto++ RANLIB=llvm-ranlib-${LLVM_VERSION} AR=llvm-ar-${LLVM_VERSION} CFLAGS=" -Wno-error" CPPFLAGS=" -Wno-error" FORCE_UNSAFE_CONFIGURE=1 ../configure --prefix=/coreutils_afpp && \
   make && make install
RUN ls /coreutils_afpp

WORKDIR /coreutils_afpp_src/obj-laf
RUN AFL_LLVM_LAF_ALL=1 CC=afl-clang-lto CXX=afl-clang-lto++ RANLIB=llvm-ranlib-${LLVM_VERSION} AR=llvm-ar-${LLVM_VERSION} CFLAGS=" -Wno-error" CPPFLAGS=" -Wno-error" FORCE_UNSAFE_CONFIGURE=1 ../configure --prefix=/coreutils_afpp_laf && \
   make && make install
RUN ls /coreutils_afpp_laf

WORKDIR /coreutils_afpp_src/obj-rq
RUN AFL_LLVM_CMPLOG=1 CC=afl-clang-lto CXX=afl-clang-lto++ RANLIB=llvm-ranlib-${LLVM_VERSION} AR=llvm-ar-${LLVM_VERSION} CFLAGS=" -Wno-error" CPPFLAGS=" -Wno-error" FORCE_UNSAFE_CONFIGURE=1 ../configure --prefix=/coreutils_afpp_rq && \
   make && make install
RUN ls /coreutils_afpp_rq

RUN git clone https://github.com/coreutils/coreutils.git /coreutils_src
RUN mkdir /coreutils_cov
RUN mkdir /coreutils_preload
RUN mkdir /coreutils_src/obj-cov
RUN mkdir /coreutils_src/obj-preload

WORKDIR /coreutils_src
RUN ./bootstrap

WORKDIR /coreutils_src/obj-cov
RUN FORCE_UNSAFE_CONFIGURE=1 ../configure --disable-nls CFLAGS=" -g -fprofile-arcs -ftest-coverage -Wno-error" --prefix /coreutils_cov && \
   make && make install
RUN ls /coreutils_cov

WORKDIR /coreutils_src/obj-preload
RUN FORCE_UNSAFE_CONFIGURE=1 ../configure --prefix /coreutils_preload && \
   make && make install
RUN ls /coreutils_preload

RUN mkdir /coreutils_src/obj-preload/src_preload
RUN cp -r /coreutils_src/obj-preload/src /coreutils_src/obj-preload/src_bin
COPY ./create_preload.sh /create_preload.sh
RUN /create_preload.sh
RUN cp /coreutils_src/obj-preload/src_preload/* /coreutils_src/obj-preload/src/
RUN mkdir -p /fuzz_data/make_check/
RUN mkdir -p /fuzz_data/scripts
COPY prep_env.py /fuzz_data/scripts/
COPY run_fuzzer.py /fuzz_data/scripts/
COPY run_cmin.py /fuzz_data/scripts/

RUN useradd -ms /bin/bash user

RUN chown -R user:user /coreutils_src
RUN chown -R user:user /fuzz_data


# TODO remove this
RUN cp /AFLplusplus/utils/argv_fuzzing/argvdump64.so /usr/local/lib/afl/argvdump64.so
RUN echo "set encoding=utf-8" > /home/user/.vimrc && \
    echo ". /etc/bash_completion" >> /home/user/.bashrc && \
    echo 'alias joe="joe --wordwrap --joe_state -nobackup"' >> /home/user/.bashrc && \
    echo "export PS1='"'[afl++ \h] \w$(__git_ps1) \$ '"'" >> /home/user/.bashrc
