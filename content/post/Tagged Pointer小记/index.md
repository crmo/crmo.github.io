---
title: "Tagged Pointer小记"
date: 2018-07-04T00:00:00+08:00
lastmod: 2018-10-07T08:13:37.000Z
url: "/2018/07/04/Tagged Pointer小记/"
tags:
  - "iOS知识小结"
draft: false
---

> 记录时间：2018.7.4

> 本文使用的测试环境是arm64架构真机

为了探究Tagged Pointer本质，可以查看runtime源码，主要看文件`objc-internal.h`。

## 宏定义

可以看到以下宏定义，只有在64位系统才支持`Tagged Pointer`。

```c
#if __LP64__
#define OBJC_HAVE_TAGGED_POINTERS 1
#endif
```

64-bit的mac，tag存储在LSB（Least Significant Bit 最低位）。其它情况比如64位的真机和模拟器，tag存储在MSB（Most Significant Bit 最高位）。

```objc
#if TARGET_OS_OSX && __x86_64__
    // 64-bit Mac - tag bit is LSB
#   define OBJC_MSB_TAGGED_POINTERS 0
#else
    // Everything else - tag bit is MSB
#   define OBJC_MSB_TAGGED_POINTERS 1
#endif

#if OBJC_MSB_TAGGED_POINTERS
#   define _OBJC_TAG_MASK (1UL<<63)
#   define _OBJC_TAG_INDEX_SHIFT 60
#   define _OBJC_TAG_SLOT_SHIFT 60
#   define _OBJC_TAG_PAYLOAD_LSHIFT 4
#   define _OBJC_TAG_PAYLOAD_RSHIFT 4
#   define _OBJC_TAG_EXT_MASK (0xfUL<<60)
#   define _OBJC_TAG_EXT_INDEX_SHIFT 52
#   define _OBJC_TAG_EXT_SLOT_SHIFT 52
#   define _OBJC_TAG_EXT_PAYLOAD_LSHIFT 12
#   define _OBJC_TAG_EXT_PAYLOAD_RSHIFT 12
#else
#   define _OBJC_TAG_MASK 1UL
#   define _OBJC_TAG_INDEX_SHIFT 1
#   define _OBJC_TAG_SLOT_SHIFT 0
#   define _OBJC_TAG_PAYLOAD_LSHIFT 0
#   define _OBJC_TAG_PAYLOAD_RSHIFT 4
#   define _OBJC_TAG_EXT_MASK 0xfUL
#   define _OBJC_TAG_EXT_INDEX_SHIFT 4
#   define _OBJC_TAG_EXT_SLOT_SHIFT 4
#   define _OBJC_TAG_EXT_PAYLOAD_LSHIFT 0
#   define _OBJC_TAG_EXT_PAYLOAD_RSHIFT 12
#endif
```

接下来是一个枚举定义，定义了默认的使用`Tagged Pointer`的类。例如NSString、NSNumber、NSIndexPath、NSDate（OBJC_TAG_NSAtom、OBJC_TAG_1、OBJC_TAG_NSManagedObjectID不知道是啥意思，还请知道的同学告诉我）。

```c
enum objc_tag_index_t : uint16_t
enum
{
    OBJC_TAG_NSAtom            = 0, 
    OBJC_TAG_1                 = 1, 
    OBJC_TAG_NSString          = 2, 
    OBJC_TAG_NSNumber          = 3, 
    OBJC_TAG_NSIndexPath       = 4, 
    OBJC_TAG_NSManagedObjectID = 5, 
    OBJC_TAG_NSDate            = 6, 
    OBJC_TAG_RESERVED_7        = 7, 

    OBJC_TAG_First60BitPayload = 0, 
    OBJC_TAG_Last60BitPayload  = 6, 
    OBJC_TAG_First52BitPayload = 8, 
    OBJC_TAG_Last52BitPayload  = 263, 

    OBJC_TAG_RESERVED_264      = 264
};
```

## 方法定义

判断是不是`Tagged Pointer`

```objc
static inline bool
_objc_isTaggedPointer(const void * _Nullable ptr) 
{
    return ((uintptr_t)ptr & _OBJC_TAG_MASK) == _OBJC_TAG_MASK;
}
```

生成一个`Tagged Pointer`，最高的4位是tagged，剩下的是数据

```objc
static inline void * _Nonnull
_objc_makeTaggedPointer(objc_tag_index_t tag, uintptr_t value)
{
    if (tag <= OBJC_TAG_Last60BitPayload) {
        return (void *)
            (_OBJC_TAG_MASK | 
             ((uintptr_t)tag << _OBJC_TAG_INDEX_SHIFT) | 
             ((value << _OBJC_TAG_PAYLOAD_RSHIFT) >> _OBJC_TAG_PAYLOAD_LSHIFT));
    } else {
        return (void *)
            (_OBJC_TAG_EXT_MASK |
             ((uintptr_t)(tag - OBJC_TAG_First52BitPayload) << _OBJC_TAG_EXT_INDEX_SHIFT) |
             ((value << _OBJC_TAG_EXT_PAYLOAD_RSHIFT) >> _OBJC_TAG_EXT_PAYLOAD_LSHIFT));
    }
}
```

从`Tagged Pointer`中取出值

```objc
static inline uintptr_t
_objc_getTaggedPointerValue(const void * _Nullable ptr) 
{
    // assert(_objc_isTaggedPointer(ptr));
    uintptr_t basicTag = ((uintptr_t)ptr >> _OBJC_TAG_INDEX_SHIFT) & _OBJC_TAG_INDEX_MASK;
    if (basicTag == _OBJC_TAG_INDEX_MASK) {
        return ((uintptr_t)ptr << _OBJC_TAG_EXT_PAYLOAD_LSHIFT) >> _OBJC_TAG_EXT_PAYLOAD_RSHIFT;
    } else {
        return ((uintptr_t)ptr << _OBJC_TAG_PAYLOAD_LSHIFT) >> _OBJC_TAG_PAYLOAD_RSHIFT;
    }
}
```

## NSNumber应用举例

可以使用下面代码来验证NSNumber如何使用`Tagged Pointer`

```objc
    NSNumber *charNumber = [NSNumber numberWithChar:'1'];
    NSNumber *shortNumber = [NSNumber numberWithShort:1];
    NSNumber *intNumber = [NSNumber numberWithInt:1];
    NSNumber *floatNumber = [NSNumber numberWithFloat:1.0];
    NSNumber *longNumber = [NSNumber numberWithLong:1];
    NSNumber *doubleNumber = [NSNumber numberWithDouble:1.0];
    
    // 输出变量的指针地址：
    // charNumber 0xb000000000000310
    // shortNumber 0xb000000000000011
    // intNumber 0xb000000000000012
    // floatNumber 0xb000000000000014
    // longNumber 0xb000000000000013
    // doubleNumber 0xb000000000000015
```

不难发现规律，都是以b(1011)开头

* 最高位是1，说明这个指针是一个`Tagged Pointer`
* 第61-63位是11（十进制是3），也就是`OBJC_TAG_NSNumber`（查上面的枚举）
* 第1-4位是NSNumber的类型：比如，char是0、short是1、int是2、float是4
* 剩下的56位就是真正的值了

## NSString应用举例

```objc
    NSString *str1 = [NSString stringWithFormat:@"a"];
    NSString *str2 = [NSString stringWithFormat:@"ab"];
    
    // 输出变量的指针地址：
    // str1: 0xa000000000000611
    // str2: 0xa000000000062612
```

与NSNumber类似

* 最高位是1，说明这个指针是一个`Tagged Pointer`
* 第61-63位是11（十进制是2），也就是`OBJC_TAG_NSString`
* 第1-4位是字符串长度
* 剩下的56位就是真正的值了

> 更多细节推荐这篇文章[采用Tagged Pointer的字符串](http://www.cocoachina.com/ios/20150918/13449.html)

---

参考文章

* [iOS Tagged Pointer](https://www.jianshu.com/p/e354f9137ba8)
* [wiki](https://en.wikipedia.org/wiki/Tagged_pointer)
* [深入理解Tagged Pointer](http://www.infoq.com/cn/articles/deep-understanding-of-tagged-pointer)

