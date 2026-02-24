---
title: "Golang编码规范"
date: 2016-11-20T22:33:54+08:00
lastmod: 2018-10-07T08:13:37.000Z
url: "/2016/11/20/Golang编码规范/"
tags:
  - "其它"
draft: false
---

- gofmt大部分的格式问题可以通过gofmt解决，gofmt自动格式化代码，保证所有的go代码与官方推荐的格式保持一致，于是所有格式有关问题，都以gofmt的结果为准。
- 行长

一行最长不超过80个字符，超过的使用换行展示，尽量保持格式优雅。

- 注释在编码阶段应该同步写好变量、函数、包的注释，最后可以利用godoc导出文档。注释必须是完整的句子，句子的结尾应该用句号作为结尾（英文句号）。注释推荐用英文，可以在写代码过程中锻炼英文的阅读和书写能力。而且用英文不会出现各种编码的问题。每个包都应该有一个包注释，一个位于package子句之前的块注释或行注释。包如果有多个go文件，只需要出现在一个go文件中即可。12// ping包实现了常用的ping相关的函数package ping

导出函数注释，第一条语句应该为一条概括语句，并且使用被声明的名字作为开头。


```
// 求a和b的和，返回sum。func Myfunction(sum int) (a, b int) {
```

- 命名需要注释来补充的命名就不算是好命名。使用可搜索的名称：单字母名称和数字常量很难从一大堆文字中搜索出来。单字母名称仅适用于短方法中的本地变量，名称长短应与其作用域相对应。若变量或常量可能在代码中多处使用，则应赋其以便于搜索的名称。做有意义的区分：Product和ProductInfo和ProductData没有区别，NameString和Name没有区别，要区分名称，就要以读者能鉴别不同之处的方式来区分 。函数命名规则：驼峰式命名，名字可以长但是得把功能，必要的参数描述清楚，函数名名应当是动词或动词短语，如postPayment、deletePage、save。并依Javabean标准加上get、set、is前缀。例如：xxx + With + 需要的参数名 + And + 需要的参数名 + …..结构体命名规则：结构体名应该是名词或名词短语，如Custome、WikiPage、Account、AddressParser，避免使用Manager、Processor、Data、Info、这样的类名，类名不应当是动词。包名命名规则：包名应该为小写单词，不要使用下划线或者混合大小写。接口命名规则：单个函数的接口名以”er”作为后缀，如Reader,Writer。接口的实现则去掉“er”。


```
type Reader interface {        Read(p []byte) (n int, err error)}
```

两个函数的接口名综合两个函数名1234type WriteFlusher interface {    Write([]byte) (int, error)    Flush() error}

 三个以上函数的接口名，抽象这个接口的功能，类似于结构体名12345type Car interface {    Start([]byte)    Stop() error    Recover()}

- 常量

常量均需使用全部大写字母组成，并使用下划线分词：


```
const APP_VER = "1.0"
```

如果是枚举类型的常量，需要先创建相应类型：


```
type Scheme stringconst (    HTTP  Scheme = "http"    HTTPS Scheme = "https")
```

如果模块的功能较为复杂、常量名称容易混淆的情况下，为了更好地区分枚举类型，可以使用完整的前缀：


```
type PullRequestStatus intconst (    PULL_REQUEST_STATUS_CONFLICT PullRequestStatus = iota    PULL_REQUEST_STATUS_CHECKING    PULL_REQUEST_STATUS_MERGEABLE)
```

- 变量变量命名基本上遵循相应的英文表达或简写,在相对简单的环境（对象数量少、针对性强）中，可以将一些名称由完整单词简写为单个字母，例如：user 可以简写为 uuserID 可以简写 uid若变量类型为 bool 类型，则名称应以 Has, Is, Can 或 Allow 开头：


```
var isExist boolvar hasConflict boolvar canManage boolvar allowGitHook bool
```

- 变量命名惯例变量名称一般遵循驼峰法，但遇到特有名词时，需要遵循以下规则：如果变量为私有，且特有名词为首个单词，则使用小写，如 apiClient其它情况都应当使用该名词原有的写法，如 APIClient、repoID、UserID错误示例：UrlArray，应该写成urlArray或者URLArray下面列举了一些常见的特有名词：


```
// A GonicMapper that contains a list of common initialisms taken from golang/lintvar LintGonicMapper = GonicMapper{    "API":   true,    "ASCII": true,    "CPU":   true,    "CSS":   true,    "DNS":   true,    "EOF":   true,    "GUID":  true,    "HTML":  true,    "HTTP":  true,    "HTTPS": true,    "ID":    true,    "IP":    true,    "JSON":  true,    "LHS":   true,    "QPS":   true,    "RAM":   true,    "RHS":   true,    "RPC":   true,    "SLA":   true,    "SMTP":  true,    "SSH":   true,    "TLS":   true,    "TTL":   true,    "UI":    true,    "UID":   true,    "UUID":  true,    "URI":   true,    "URL":   true,    "UTF8":  true,    "VM":    true,    "XML":   true,    "XSRF":  true,    "XSS":   true,}
```

- struct规范

struct申明和初始化格式采用多行：

定义如下：


```
type User struct{    Username  string    Email     string}
```

初始化如下：


```
u := User{    Username: "test",    Email:    "test@gmail.com",}
```

- 控制结构ifif接受初始化语句，约定如下方式建立局部变量


```
if err := file.Chmod(0664); err != nil {    return err}
```

 for采用短声明建立局部变量


```
sum := 0for i := 0; i < 10; i++ {    sum += i}
```

 return尽早return：一旦有错误发生，马上返回


```
f, err := os.Open(name)if err != nil {    return err}d, err := f.Stat()if err != nil {    f.Close()    return err}codeUsing(f, d)
```

- 错误处理error作为函数的值返回,必须对error进行处理错误描述如果是英文必须为小写，不需要标点结尾采用独立的错误流进行处理不要采用下面的处理错误写法


```
if err != nil {    // error handling} else {    // normal code}
```

 采用下面的写法


```
if err != nil {    // error handling    return // or continue, etc.}// normal code
```

 使用函数的返回值时，则采用下面的方式


```
x, err := f()if err != nil {    // error handling    return}// use x
```

- panic

尽量不要使用panic，除非你知道你在做什么

- import

对import的包进行分组管理，用换行符分割，而且标准库作为分组的第一组。如果你的包引入了三种类型的包，标准库包，程序内部包，第三方包，建议采用如下方式进行组织你的包


```
package mainimport (    "fmt"    "os"    "kmg/a"    "kmg/b"    "code.google.com/a"    "github.com/b")
```

 在项目中不要使用相对路径引入包：


```
// 错误示例import “../net”// 正确的做法import “github.com/repo/proj/src/net”
```

goimports会自动帮你格式化

- 参数传递对于少量数据，不要传递指针对于大量数据的struct可以考虑使用指针传入参数是map，slice，chan不要传递指针，因为map，slice，chan是引用类型，不需要传递指针的指针
- 单元测试

单元测试文件名命名规范为 example_test.go测试用例的函数名称必须以 Test 开头，例如：TestExample
