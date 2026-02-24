---
title: "探寻Objective-C引用计数本质"
description: "从 Runtime 源码层面剖析 Objective-C 引用计数的存储与操作原理，包括 NONPOINTER ISA 中 extra_rc 的位布局、SideTable 溢出机制，以及 retain/release 的完整实现流程。"
date: 2018-05-26T00:00:00+08:00
lastmod: 2018-10-07T08:16:32.000Z
url: "/2018/05/26/探寻Objective-C引用计数本质/"
tags:
  - "iOS知识小结"
draft: false
---

> 本文涉及到的CPU架构为arm64，其它架构大同小异。
> 源码来自[苹果开源-runtime](https://opensource.apple.com/tarballs/objc4/)。

Objective-C中采用引用计数机制来管理内存，在MRC时代，需要我们手动`retain`和`release`，在苹果引入ARC后大部分时间我们不用再关心引用计数问题。但是为了深入Objective-C本质，引用计数究竟是怎么实现的还是值得我们去探寻的。

## ISA

OC中的对象的实质其实是结构体，其中大部分对象都有isa，指向类对象（有一种神奇的存在叫做`Tagged Pointer`），源码中关于对象结构体`objc_object`定义如下：

```c
// objc-private.h
struct objc_object {
private:
    isa_t isa;
public:
    id retain();
    void release();
    id autorelease();
    ... //省略了其它方法，感兴趣可以直接看源码
```

### Tagged Pointer

除了有一种特殊的对象`Tagged Pointer`，这种类型的对象值就存在指针当中，存取性能高。可以用来存储少量数据的对象，例如NSNumber、NSDate、NSString。(更多Tagged Pointer知识，推荐这篇[文章](http://www.infoq.com/cn/articles/deep-understanding-of-tagged-pointer))。也就没有引用计数、内存释放的问题。

### NONPOINTER ISA

arm64架构isa占64位，苹果为了优化性能，存储类对象地址只用了33位，剩下的位用来存储一些其它信息，比如本文讨论的引用计数。

NONPOINTER ISA存储的字段定义如下：

```
# if __arm64__
#   define ISA_MASK        0x0000000ffffffff8ULL
#   define ISA_MAGIC_MASK  0x000003f000000001ULL
#   define ISA_MAGIC_VALUE 0x000001a000000001ULL
    struct {
        uintptr_t nonpointer        : 1;
        uintptr_t has_assoc         : 1;
        uintptr_t has_cxx_dtor      : 1;
        uintptr_t shiftcls          : 33; // MACH_VM_MAX_ADDRESS 0x1000000000
        uintptr_t magic             : 6;
        uintptr_t weakly_referenced : 1;
        uintptr_t deallocating      : 1;
        uintptr_t has_sidetable_rc  : 1;
        uintptr_t extra_rc          : 19;
#       define RC_ONE   (1ULL<<45)
#       define RC_HALF  (1ULL<<18)
    };
```

## extra_rc

那引用计数存在哪里呢？秘密就在`extra_rc`中。

> extra_rc只是存储了额外的引用计数，实际的引用计数计算公式：`引用计数=extra_rc+1`。

`extra_rc`占了19位，可以存储的最大引用计数：$2^{19}-1+1=524288$，超过它就需要进位到`SideTables`。SideTables是一个Hash表，根据对象地址可以找到对应的`SideTable`，`SideTable`内包含一个`RefcountMap`，根据对象地址取出其引用计数，类型是`size_t`。
它是一个`unsigned long`，最低两位是标志位，剩下的62位用来存储引用计数。我们可以计算出引用计数的理论最大值：$2^{62+19}=2.417851639229258e24$。

> 其实isa能存储的524288在日常开发已经完全够用了，为什么还要搞个Side Table？我猜测是因为历史问题，以前cpu是32位的，isa中能存储的引用计数就只有$2^{7}=128$。因此在arm64下，引用计数通常是存储在isa中的。

## retain

有了前面的铺垫，我们知道引用计数怎么存储的了，那引用计数又是怎么改变的呢？通过剖析`retain`源码我们就可以得出结论了。
objc_object的方法全部定义在objc-object.h文件中，全是内联函数，应该是为了性能的考虑。

我们来看看`retain`的函数定义

```c
inline id 
objc_object::retain()
{
    assert(!isTaggedPointer());

    if (fastpath(!ISA()->hasCustomRR())) {
        return rootRetain();
    }

    return ((id(*)(objc_object *, SEL))objc_msgSend)(this, SEL_retain);
}
```

这层比较简单，做了三件事情：

1. 判断指针是不是`Tagged Pointer`
2. 判断是否有自定义`retain`，如果有调用自定义的。
3. 最后调用`rootRetain`

我们来看看关键函数`rootRetain`的实现（为了便于阅读，代码有所删减）

```c
ALWAYS_INLINE id 
objc_object::rootRetain(bool tryRetain, bool handleOverflow)
{
    isa_t oldisa;
    isa_t newisa;

    // 加锁，用汇编指令ldxr来保证原子性
    oldisa = LoadExclusive(&isa.bits);
    newisa = oldisa;
    
    if (newisa.nonpointer = 0) {
        // newisa.nonpointer = 0说明所有位数都是地址值
        // 释放锁，使用汇编指令clrex
        ClearExclusive(&isa.bits);
        
        // 由于所有位数都是地址值，直接使用sidetable来存储引用计数
        return sidetable_retain();
    }
    
    // 存储extra_rc++后的结果
    uintptr_t carry;
    // extra_rc++
    newisa.bits = addc(newisa.bits, RC_ONE, 0, &carry);
    
    if (carry == 0) {
        // extra_rc++后溢出，进位到side table
        newisa.extra_rc = RC_HALF;
        newisa.has_sidetable_rc = true;
        sidetable_addExtraRC_nolock(RC_HALF);
    }
        
    // 将newisa写入isa
    StoreExclusive(&isa.bits, oldisa.bits, newisa.bits)
    return (id)this;
}
```

有一个细节可以了解下，如何用汇编来实现原子性操作。

```c
static ALWAYS_INLINE
uintptr_t 
LoadExclusive(uintptr_t *src)
{
    uintptr_t result;
    // 在多核CPU下，对一个地址的访问可能引起冲突，ldxr解决了冲突，保证原子性。
    asm("ldxr %x0, [%x1]" 
        : "=r" (result) 
        : "r" (src), "m" (*src));
    return result;
}
```

## release

`release`代码逻辑基本上就是`retain`反过来走一遍，有点不同的是在引用计数减到0时，会调用对象的dealloc方法。

```
ALWAYS_INLINE bool
objc_object::rootRelease(bool performDealloc, bool handleUnderflow)
{
    isa_t oldisa;
    isa_t newisa;
    
retry:
    oldisa = LoadExclusive(&isa.bits);
    newisa = oldisa;
    if (newisa.nonpointer == 0) {
        ClearExclusive(&isa.bits);
        if (sideTableLocked) sidetable_unlock();
        return sidetable_release(performDealloc);
    }
    
    uintptr_t carry;
    // extra_rc--
    newisa.bits = subc(newisa.bits, RC_ONE, 0, &carry);
    if (carry == 0) {
        // 需要从SideTable借位，或者引用计数为0
        goto underflow;
    }
    
    // 存储引用计数到isa
    StoreReleaseExclusive(&isa.bits,
                          oldisa.bits, newisa.bits)
    return false;
    
underflow:
    // 从SideTable借位
    // 或引用计数为0，调用delloc
    
    // 此处省略N多代码
    // 总结一下:修改Side Table与extra_rc，
    
    // 引用计数减为0时，调用dealloc
    if (performDealloc) {
        ((void(*)(objc_object *, SEL))objc_msgSend)(this, SEL_dealloc);
    }
    return true;
}
```

## 小结

> 引用计数存在哪？

1. `Tagged Pointer`不需要引用计数
2. `NONPOINTER ISA`(isa的第一位为1)的引用计数优先存在isa中，大于524288了进位到`Side Tables`
3. 非`NONPOINTER ISA`引用计数存在`Side Tables`

> retain/release的实质

* 找到引用计数存储区域，然后+1/-1
* 如果是`NONPOINTER ISA`，还要处理进位/借位的情况
* release在引用计数减为0时，调用`dealloc`

------

参考

* [黑箱中的 retain 和 release](https://github.com/Draveness/analyze/blob/master/contents/objc/黑箱中的%20retain%20和%20release.md)
* [深入理解Tagged Pointer](http://www.infoq.com/cn/articles/deep-understanding-of-tagged-pointer)

