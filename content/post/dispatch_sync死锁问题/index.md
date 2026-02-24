---
title: "dispatch_sync死锁问题"
description: "分析 GCD 中 dispatch_sync 导致死锁的典型场景，包括单队列嵌套和多队列交叉两种情况，并指出使用 dispatch_get_current_queue 防死锁的误区。"
date: 2018-08-03T00:00:00+08:00
lastmod: 2018-10-07T08:13:37.000Z
url: "/2018/08/03/dispatch_sync死锁问题/"
tags:
  - "iOS知识小结"
draft: false
---

> 2018.8.3

## 问题分析

使用`dispatch_sync`的时候要小心谨慎，稍不注意就会导致死锁问题，先看两个典型的案例：

案例一

```objective-c
- (void)deadlock1 {
    dispatch_queue_t queue = dispatch_queue_create("label", DISPATCH_QUEUE_SERIAL);
    dispatch_sync(queue, ^{
        dispatch_sync(queue, ^{
            NSLog(@"");
        });
    });
}
```

案例二

```objective-c
- (void)deadlock2 {
    dispatch_queue_t queue1 = dispatch_queue_create("label", DISPATCH_QUEUE_SERIAL);
    dispatch_queue_t queue2 = dispatch_queue_create("label", DISPATCH_QUEUE_SERIAL);
    dispatch_sync(queue1, ^{
        dispatch_sync(queue2, ^{
            dispatch_sync(queue1, ^{
                NSLog(@"");
            });
        });
    });
}
```

上面两个案例死锁的原因都是同一个串行队列的任务相互等待。 当然实际工程中遇到的死锁问题会更加复杂，难以分析。

## 典型误区

在阅读相关书籍、博客都提到了一个方法`dispatch_get_current_queue()`，通过这个方法可以获取到当前队列，于是有人就用它来解决死锁问题。

```objective-c
- (void)safeSync:(void(^)())block {
    if (!block) {
        return;
    }
    if (dispatch_get_current_queue() == queue) {
        block();
    } else {
        dispatch_sync(queue, ^{
            block();
        });
    }
}
```

第一眼看起来天衣无缝，对于案例一的确可以完美解决，但是对于案例二这种对队列的情况就判断不了。难怪苹果在iOS6就注释了这个方法。


---
推荐阅读：

[Thread-Safe Class Design](https://www.objc.io/issues/2-concurrency/thread-safe-class-design/#pitfalls-of-gcd)