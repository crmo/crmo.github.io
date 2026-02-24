---
title: "浅析AutoreleasePool源码"
description: "分析 AutoreleasePool 源码中 pop 操作后清理空 page 的策略，解读 releaseUntil 和 kill 方法的实现，说明系统根据当前 page 使用率决定保留或释放 child page 的内存优化逻辑。"
date: 2018-04-14T15:31:00+08:00
lastmod: 2018-10-07T08:13:37.000Z
url: "/2018/04/14/浅析AutoreleasePool源码/"
tags:
  - "源码学习"
draft: false
---

最近在拜读Draveness大佬的一篇文章[自动释放池的前世今生 ---- 深入解析 autoreleasepool](https://draveness.me/autoreleasepool)，看到文中给读者留了一个问题：

> 我到现在也不是很清楚为什么要根据当前页的不同状态 kill 掉不同 child 的页面。

关于`AutoreleasePool`是什么，强力推荐阅读原文，写的很好。这里就不说了，直接讨论问题。

首先是整个`pop`方法的实现：

```
    static inline void pop(void *token) 
    {
        AutoreleasePoolPage *page;
        id *stop;

        if (token == (void*)EMPTY_POOL_PLACEHOLDER) {
            // Popping the top-level placeholder pool.
            if (hotPage()) {
                // Pool was used. Pop its contents normally.
                // Pool pages remain allocated for re-use as usual.
                pop(coldPage()->begin());
            } else {
                // Pool was never used. Clear the placeholder.
                setHotPage(nil);
            }
            return;
        }

        page = pageForPointer(token);
        stop = (id *)token;
        if (*stop != POOL_BOUNDARY) {
            if (stop == page->begin()  &&  !page->parent) {
                // Start of coldest page may correctly not be POOL_BOUNDARY:
                // 1. top-level pool is popped, leaving the cold page in place
                // 2. an object is autoreleased with no pool
            } else {
                // Error. For bincompat purposes this is not 
                // fatal in executables built with old SDKs.
                return badPop(token);
            }
        }

        if (PrintPoolHiwat) printHiwat();

        page->releaseUntil(stop);

        // memory: delete empty children
        if (DebugPoolAllocation  &&  page->empty()) {
            // special case: delete everything during page-per-pool debugging
            AutoreleasePoolPage *parent = page->parent;
            page->kill();
            setHotPage(parent);
        } else if (DebugMissingPools  &&  page->empty()  &&  !page->parent) {
            // special case: delete everything for pop(top) 
            // when debugging missing autorelease pools
            page->kill();
            setHotPage(nil);
        } 
        else if (page->child) {
            // hysteresis: keep one empty child if page is more than half fully
            if (page->lessThanHalfFull()) {
                page->child->kill();
            }
            else if (page->child->child) {
                page->child->child->kill();
            }
        }
    }
```

我们先看看释放的函数`releaseUntil `，它在释放的时候其实会一直顺着`parent`往前释放，直到参数`stop`，也就是说可能一次性释放好几个`page`。

```
// 代码有所删减
void releaseUntil(id *stop)
{
    while (this->next != stop) {
        AutoreleasePoolPage *page = hotPage();
        
        while (page->empty()) {
            page = page->parent;
            setHotPage(page);
        }
        
        id obj = *--page->next;
        memset((void*)page->next, SCRIBBLE, sizeof(*page->next));
        
        if (obj != POOL_BOUNDARY) {
            objc_release(obj);
        }
    }
    
    setHotPage(this);
}
```

然后我们来看看这段有疑问的代码

```
        // memory: delete empty children
        if (DebugPoolAllocation  &&  page->empty()) {  // 分支1
            // special case: delete everything during page-per-pool debugging
            AutoreleasePoolPage *parent = page->parent;
            page->kill();
            setHotPage(parent);
        } else if (DebugMissingPools  &&  page->empty()  &&  !page->parent) { // 分支2
            // special case: delete everything for pop(top) 
            // when debugging missing autorelease pools
            page->kill();
            setHotPage(nil);
        } 
        else if (page->child) { // 分支3
            // hysteresis: keep one empty child if page is more than half fully
            if (page->lessThanHalfFull()) {
                page->child->kill();
            }
            else if (page->child->child) {
                page->child->child->kill();
            }
        }
```

这块代码的作用是删除空的子节点，释放内存。pop之后三种情况：
1. 当前`page`为空，直接kill掉当前`page`，然后把`parent`设置为`hotpage`；
2. 当前`page`为空，而且没有`parent`，kill掉当前`page`，`hotpage`置为空；
3. 当前`page`不为空，但是有`child`，如果当前`page`的空间占用不到一半，释放`child`，如果当前`page`的空间占用超过一半，且`child`还有`child`，直接释放这个孙子辈的`page`。（对于第三步注释中的解释是：keep one empty child if page is more than half fully）

我们再看看`kill`的实现，可以发现他是会顺着`child`一直往后释放，保证释放节点的`child page`都被释放了。

```
void kill()
{
    AutoreleasePoolPage *page = this;
    while (page->child) page = page->child;
    
    AutoreleasePoolPage *deathptr;
    do {
        deathptr = page;
        page = page->parent;
        if (page) {
            page->unprotect();
            page->child = nil;
            page->protect();
        }
        delete deathptr;
    } while (deathptr != this);
}
```

到这里就可以得出结论了：
1. pop之后，所有`child page`肯定都为空了，且当前`page`一定是`hotPage`
2. 系统为了节约内存，判断，如果当前`page`空间使用少于一半，就释放掉所有的`child page`，如果当前`page`空间使用大于一半，就从孙子`page`开始释放，预留一个`child page`。

