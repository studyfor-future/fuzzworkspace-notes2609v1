# ICPilot-AFL++

ICPilot-AFL++ 是基于 AFL++ 改造的模糊测试核心

---

## 编译部署方式

推荐 Linux 环境。

### 常用编译安装

```bash
make -j"$(nproc)" distrib
make install
```

如果只想编译主要二进制：

```bash
make -j"$(nproc)" all
```

如果只关注源码插桩路径：

```bash
make -j"$(nproc)" source-only
```

### 指定 LLVM 版本

当系统里有多个 LLVM 版本时：

```bash
make LLVM_CONFIG=llvm-config-18 distrib
```

将 `llvm-config-18` 替换为你机器上的实际版本。

### 清理后重编

```bash
make clean
make -j"$(nproc)" distrib
```

---

## 使用方式

### 1. 用包装器编译目标

```bash
./afl-cc -o target target.c
```

或：

```bash
afl-cc -o target target.c
```

### 2. 启动 LinUCB 模式模糊测试

```bash
./afl-fuzz -i in -o out -p linucb -- ./target
```

示例：

```bash
./afl-fuzz -i seeds -o findings -p linucb -- ./target
```

---

## 宏与开关说明

### `__POLAR_INS(token)`
这是 ICPilot 支持的语义标记宏，用于把额外的语义/风险信号桥接进 fuzzing 流程。

示意：

```c
__POLAR_INS(token)
```

### `-p linucb`
这是运行时调度开关，用于启用 LinUCB 引导的队列优先级模式。

```bash
./afl-fuzz -i in -o out -p linucb -- ./target @@
```

### `include/config.h`
仓库中保留了编译期开关与配置钩子，适合放置项目级功能开关
