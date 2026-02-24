---
title: "计算文字长度"
date: 2018-07-09T00:00:00+08:00
lastmod: 2018-10-07T08:13:37.000Z
url: "/2018/07/09/计算文字长度/"
tags:
  - "iOS知识小结"
draft: false
---

> 2018.7.9

> [官方文档](https://developer.apple.com/documentation/foundation/nsstring/1524729-boundingrectwithsize?language=occ)


## 方法定义

```objectivec
- (NSRect)boundingRectWithSize:(NSSize)size 
                       options:(NSStringDrawingOptions)options 
                    attributes:(NSDictionary<NSAttributedStringKey, id> *)attributes 
                       context:(NSStringDrawingContext *)context;
```

## 参数定义

### size

绘制的限制size，计算出来的值不会超过这个大小。

### options

一些配置项。定义如下：

```objectivec
typedef NS_OPTIONS(NSInteger, NSStringDrawingOptions) {
    NSStringDrawingUsesLineFragmentOrigin = 1 << 0, // The specified origin is the line fragment origin, not the base line origin
    NSStringDrawingUsesFontLeading = 1 << 1, // Uses the font leading for calculating line heights
    NSStringDrawingUsesDeviceMetrics = 1 << 3, // Uses image glyph bounds instead of typographic bounds
    NSStringDrawingTruncatesLastVisibleLine NS_ENUM_AVAILABLE(10_5, 6_0) = 1 << 5, // Truncates and adds the ellipsis character to the last visible line if the text doesn't fit into the bounds specified. Ignored if NSStringDrawingUsesLineFragmentOrigin is not also set.

} NS_ENUM_AVAILABLE(10_0, 6_0);
```

实际测试使用`NSStringDrawingUsesLineFragmentOrigin|NSStringDrawingUsesFontLeading`可以满足需求，`NSStringDrawingUsesLineFragmentOrigin`是必须的，`NSStringDrawingUsesFontLeading`加不加在测试的时候没发现区别，但是在[stackoverflow相关讨论](https://stackoverflow.com/questions/13621084/boundingrectwithsize-for-nsattributedstring-returning-wrong-size/15399767#15399767)里加上了，留个坑，后面知道为什么了来补充吧。

### attributes

字体

### context

上下文

### 注意事项

1. 如果是多行文字，options要加上`NSStringDrawingUsesLineFragmentOrigin`
2. 返回的值是小数，需要调用`ceil`向上取整
3. 得到的宽度可能比实际宽

## 代码示例

```objectivec
+ (CGSize)getTextLabelSize:(NSString *)message {
    if ([message length] > 0) {
        // 文本框的最大宽度
        float maxWidth = 200;
        CGRect textRect = [message
                           boundingRectWithSize:CGSizeMake(maxWidth, CGFLOAT_MAX)
                           options:(NSStringDrawingUsesLineFragmentOrigin |
                                    NSStringDrawingUsesFontLeading)
                           attributes:@{
                                        NSFontAttributeName :
                                            [UIFont systemFontOfSize:16]
                                        }
                           context:nil];
        textRect.size.height = ceilf(textRect.size.height);
        textRect.size.width = ceilf(textRect.size.width);
        return CGSizeMake(textRect.size.width, textRect.size.height);
    } else {
        return CGSizeZero;
    }
}
```