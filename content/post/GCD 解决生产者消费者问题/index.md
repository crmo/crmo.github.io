---
title: "GCD 解决生产者消费者问题"
date: 2019-06-16T00:00:00+08:00
lastmod: 2019-06-16T03:55:13.000Z
url: "/2019/06/16/GCD 解决生产者消费者问题/"
tags:
  - "iOS知识小结"
draft: false
---

说起生产者消费者问题（Producer-consumer problem），相信大家都印象深刻，有遗忘可以看看[wiki](https://zh.wikipedia.org/wiki/生产者消费者问题#使用信号灯的算法)上的解释，我们今天来聊聊怎么用 GCD 实现一个生产者消费者模型。

我们先理一下思路，看看问题关键点：
1. 生产者生成产品放到缓冲区中，然后重复此过程，但是生产的产品数量不能超过缓冲区大小，如果缓冲区满了，停止生产新的产品，等待缓冲区有空位；
2. 消费者不停从缓冲区取出产品，如果缓冲区空了，则停止消费，等待新的产品放到缓冲区中；

很容易就联想到信号量 `dispatch_semaphore_t` ，我们需要使用两个信号量分别控制`生产者`与`消费者`，`semaphoreProduce` 控制生产者当缓冲区满时停止生产，`semaphoreConsume` 控制消费者当缓冲区空时停止消费。如下图所示（配图纯手工制作，轻喷😂）：

![灵魂画手配图✌️](IMG_0010.jpg)


Show me the code.

```oc
// 控制生产者的信号量
dispatch_semaphore_t semaphoreProduce;
// 控制消费者的信号量
dispatch_semaphore_t semaphoreConsume;
// 当前产品数量
int productCount = 0;
// 缓冲区大小
const int bufferSize = 5;

// 初始化生产者、消费者信号量
- (void)initProducerAndConsume {
    // 初始化缓冲区大小
    semaphoreProduce = dispatch_semaphore_create(bufferSize);
    semaphoreConsume = dispatch_semaphore_create(0);
}

// 生产商品
- (void)produce {
    dispatch_async(dispatch_get_global_queue(0, 0), ^{
        dispatch_semaphore_wait(semaphoreProduce, DISPATCH_TIME_FOREVER);
        [NSThread sleepForTimeInterval:1];
        productCount++;
        NSLog(@"生产商品，商品总量：%d", productCount);
        dispatch_semaphore_signal(semaphoreConsume);
    });
}

// 消费商品
- (void)consume {
    dispatch_async(dispatch_get_global_queue(0, 0), ^{
        dispatch_semaphore_wait(semaphoreConsume, DISPATCH_TIME_FOREVER);
        [NSThread sleepForTimeInterval:1];
        productCount--;
        NSLog(@"消费商品，商品总量：%d", productCount);
        dispatch_semaphore_signal(semaphoreProduce);
    });
}
```