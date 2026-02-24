---
title: "UITextField控制输入长度"
description: "介绍 UITextField 限制输入长度的实现思路，处理 emoji 组合字符截断和中文输入高亮状态下的长度计算问题。"
date: 2018-07-06T00:00:00+08:00
lastmod: 2018-10-07T08:13:37.000Z
url: "/2018/07/06/UITextField控制输入长度/"
tags:
  - "iOS知识小结"
draft: false
---

> 2018.7.6

有些时候会有控制输入框文字长度的需求，记录一个简单的思路。

```oc
- (BOOL)textField:(UITextField *)textField shouldChangeCharactersInRange:(NSRange)range replacementString:(NSString *)string {
    if (string.length == 0) {
        return YES;
    }
    
    NSInteger limit = 15; // 文本的最大长度
    NSString *newStr = [textField.text stringByAppendingString:string]; // 修改之后的新字符串
    NSInteger newStrLength = newStr.length;
    newStrLength -= [textField textInRange:[textField markedTextRange]].length; // 去掉高亮内容，输入中文拼音的情况
    
    if (newStrLength > limit) {
        // 处理composed character, 比如emoji
        NSString *tempStr = [newStr substringWithRange:[newStr rangeOfComposedCharacterSequencesForRange:NSMakeRange(0, limit)]];
        textField.text = tempStr;
        return NO;
    }
    
    return YES;
}
```

有两个坑注意下：

1. emoji是`composed character`，它是由多个字符组合，长度不是1。最开始用的`substringToIndex`会导致最后一个emoji乱码。
2. 计算长度的时候要去掉中文输入的时候高亮部分

