---
tags:
    - 后端
    - spring
---
# 项目实战
版本：springboot2.6.12，springsession2.6.3

依赖：

```xml
        <!--spring session starter-->
<dependency>
    <groupId>org.springframework.session</groupId>
    <artifactId>spring-session-data-redis</artifactId>
</dependency>
        <!--spring redis starter-->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-redis</artifactId>
</dependency>
```

配置：

```yaml
spring:
  session:
    store-type: redis
    redis:
      flush-mode: on_save # Sessions flush mode.
      namespace: spring:session #spring session的redis key前缀
  redis:
    host: 192.168.7.65
    port: 6379
server:
  servlet:
    session:
      timeout: 30m
```

配置类中

+ 注意：<font style="color:#DF2A3F;">springboot项目不需要添加@EnableSpringHttpSession，而是通过自动配置类SessionAutoConfiguration生效</font>

# 启动流程
配置类：

![画板](/assets/images/1676259244117-e42c8ae8-3b54-4f87-a2f4-c661f0e836b6.jpeg)

+ SessionConfigurationImportSelector：根据web容器的类型是servlet或reactive动态引入session存储仓库的配置类，默认会引入redis、jdbc、mongodb、none的存储仓库
+ SpringBootRedisHttpSessionConfiguration：会使用配置文件对应的ServerProperties和SessionProperties中的配置，创建web过滤器和redis session存储仓库的bean

# 会话处理逻辑
![画板](/assets/images/1676288075129-6daf1a55-9b87-4fd5-a998-f1cab69ecdd2.jpeg)

web过滤器SessionRepositoryFilter拦截请求执行，将原始请求包装成SessionRepositoryRequestWrapper，从而实现自定义创建会话方法getSession，过滤器执行结束或者响应提交时，执行commitSession

+ 创建会话(getSession)：根据cookie中的sessionId，调用会话仓库RedisIndexedSessionRepository的findById获取已存在的未过期会话，如果会话不存在或者过期则返回null，这时创建会话对象RedisSession，属性：1、会话id，uuid。2、创建时间。3、空闲过期时间。4、最近访问时间。创建完成后将会话保存为请求的属性
+ 提交会话(commitSession)：获取当前请求对应的会话，保存到redis，每个会话对应3个redis key，1个用来保存会话属性，另外2个用来触发和监听redis key过期事件，从而执行进程本地的spring会话过期事件SessionExpiredEvent。保存成功后，会发布一个redis 会话创建事件，从而触发其它实例的spring会话创建事件SessionCreatedEvent.。

```plain
//真正的会话属性，它的过期时间是真正的过期时间+5min，这样做是为了在监听key过期时，还能从redis查到会话的属性，从而创建过期会话对象保存到过期事件对象中，根本原因是因为redis key通知机制只会给出发生变更的key，没有value
hput spring:session:session:[sessionId] [sessionData]
expire spring:session:session:[sessionId] maxInactiveInterval+5min
//值为空的key，当监听到会话过期时，只会删除它，还可以获取到会话的属性
set spring:session:expires:[sessionId] ""
expire spring:session:expires:[sessionId] maxInactiveInterval
//解决redis key过期时不一定会立刻发布事件的问题，会话在生成过期时间时，不会使用准确到毫秒的时间戳，而是时间戳的下一分钟，这样使得更多的会话过期时间相同，把它们加到过期时间为key、会话id为value的set里，用一个定时任务每隔1分钟查询上一分钟过期的会话id，查询会话id，触发key过期事件
sadd spring:session:expirations:[expireTimeStamp] expires:[sessionId]
expire spring:session:expirations:[expireTimeStamp] maxInactiveInterval+5min
//发布会话创建事件
public spring:session:event:0:created:[sessionId] [sessionData]
```

## redis key通知机制
[Redis keyspace notifications](https://redis.io/docs/manual/keyspace-notifications/#configuration)

redis key发生变更、并且配置了notify-keyspace-events时，会在2个通道上发布事件：

1. 通道名称：发生变更的key名称，__keyspace@[database]__:[keyname]。事件值：对key的操作类型，比如set，hset，sadd，srem，expire(设置过期时间)，expired(已过期)
2. 通道名称：对key的操作类型，__keyevent@[database]__:[type]。时间值：发生变更的key名称

```bash
$ redis-cli config set notify-keyspace-events KEA
$ redis-cli --csv psubscribe __key*
Reading messages... (press Ctrl-C to quit)
"psubscribe","__key*",1
"pmessage","__key*","__keyspace@0__:k1","set"
"pmessage","__key*","__keyevent@0__:set","k1"
"pmessage","__key*","__keyspace@0__:h1","hset"
"pmessage","__key*","__keyevent@0__:hset","h1"
"pmessage","__key*","__keyspace@0__:k1","set"
"pmessage","__key*","__keyevent@0__:set","k1"
"pmessage","__key*","__keyspace@0__:s1","sadd"
"pmessage","__key*","__keyevent@0__:sadd","s1"
"pmessage","__key*","__keyspace@0__:s1","srem"
"pmessage","__key*","__keyevent@0__:srem","s1"
"pmessage","__key*","__keyspace@0__:k1","expire"
"pmessage","__key*","__keyevent@0__:expire","k1"
"pmessage","__key*","__keyspace@0__:k1","expired"
"pmessage","__key*","__keyevent@0__:expired","k1"
"pmessage","__key*","__keyspace@0__:h1","hdel"
"pmessage","__key*","__keyevent@0__:hdel","h1"
```

notify-keyspace-events配置：

+ 通过K和E配置发布keyspace事件还是keyevent事件
+ lshzt配置string、list、set、hash、zset、stream类型发生变更时发布事件
+ g配置所有数据类型发生变更发布事件
+ x配置key过期时发布expired事件
+ e配置key淘汰时发布事件

坑点：

+ 事件数据中只有key，没有对应的值，如果要在过期时获取值，需要客户端实现，比如使用一个值为空的key，给它设置过期事件，过期时，通过key名称得到真正存储值的key名称，从而得到值，真正存储值的key可以设置一个真正过期时间更晚一些的时间
+ 过期事件不一定在刚好过期时发布，而是在客户端查询或redis后台扫描过期key的定时任务执行时，发现key过期，再触发过期事件。因此也需要客户端实现定时查询任务，触发过期事件的发布
+ 只有key变更时才会发布事件，查询(get、lindex、llen)、srem和zrem删除不存在的元素、hrem删除不存在的属性不会发布，set和hset重复的值会发布

