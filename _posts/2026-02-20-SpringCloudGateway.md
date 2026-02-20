---
tags:
    - 后端
    - spring
---
# 作用
+ 统一管理，易于监控
+ 安全，限流：在网关层就过滤掉非法信息
+ nginx外部网关，gateway内网
+ nginx可以使用Lua或Kong来增强

# 概念
+ id:名称随意
+ uri: 被代理的服务地址。id和uri必填，谓词和过滤器非必填
+ 谓词：可以用于匹配访问gateway的uri，匹配则当前路由生效，
+ 过滤器：GatewayFilter的实例，在代理之前或之后添加逻辑，灵活度最高

# 处理流程
+ 首先Handler Mapping对URL进行处理，再交给Web Handler，它调用被过滤器前半部分进行处理，处理完成后调用真实被代理的服务，被代理的服务响应后，执行过滤器后半部分的逻辑，把结果返回给WebHandler，再返回给HandlerMapping，最终返回给客户端

# 使用
```bash
gateway:
      discovery:
        locator:
          enabled: true # 启用自动根据服务ID生成路由
          lower-case-service-id: true # 设置路由的路径为小写的服务ID
```

# yml配置
+ list中的元素如果有多个字段，需要"-"和冒号分别指定每个字段和值；如果只有一个字段，可以使用逗号分割
+ 对象类型的配置，可以通过"-"和冒号配置每个字段
+ Map类型：key,value通过冒号分割

```bash
predicates:
  - Path=/sendOrder
  - Query=name,ma.
  - name: Query
    args:
      param: id
      regexp: \d+
 #predicates是List, 它的元素是
 public class PredicateDefinition {

	@NotNull
	private String name;

	private Map<String, String> args = new LinkedHashMap<>();
  }
  等号分割转成对象的写法不是yml内置支持的
```

# 谓词
+ 谓词配置是一个List，其中的元素可以是特定格式的字符串，或者对象。字符串写法：等号分割，第1部分是谓词名称name，第二部分args逗号分割，值保存进Map value，Map key自动生成。对象写法：PredicateDefinition
+ 如果args中本身有逗号和冒号，就不能使用字符串格式
+ shortcutType方法定义了args参数到ConfigClass的解析方式，DEFAULT：shortcutFieldOrder去掉shortcutFieldPrefix前缀对应ConfigClass字段名称，args参数的val对应ConfigClass的字段值；GATHER_LIST：逗号分割的List；GATHER_LIST_TAIL_FLAG：逗号分割的List，但最后一个值是布尔值，最终转成2个key的Map，第一个key的值是布尔值前面的List，第二个是布尔值
+ 用于匹配访问gateway的请求(比如uri,查询参数、请求头)，匹配则当前路由生效
+ 对应GatewayPredicate的实现，实现类由工厂创建，工厂是RoutePredicateFactory的实现类，实现类命名规范：谓词name+RoutePredicateFactory，比如Path对应PathRoutePredicateFactory
+ 谓词名称对应工厂实现类的类名前缀，谓词参数args对应工厂ConfigClass
+ 多个谓词是**且**的关系
+ 谓词不通过时，gateway返回404

Path

+ 匹配路径，支持ant匹配和通过{}提取uriVariables

Query

+ 是否有对应http请求参数名称，值可以正则。
+ name固定Query，args有2个值，param和regexp，对应查询参数名称和值
+ 只配名称时，表示只要有该请求参数则通过

Header

+ HeaderRoutePredicateFactory
+ 匹配请求头的名称和值，可以只配名称，实际请求头的值可能有多个，只要有一个匹配即可，配置值支持正则

Method

+ 匹配HTTP请求方法，配置必须大写，逗号分割

RemoteAddr

+ 匹配请求的客户端ip，准确的说是最后一个网络代理的ip，可以多个，逗号分割

Host

+ 匹配Host请求头中主机部分的值（不包括端口），可以多个，逗号分割，可以ant匹配
+ 采用AntPathMatcher匹配，且路径分割符是"."

Cookie

+ 匹配Cookie的名称和值，值可以正则匹配

Weight

+ 用于不同路由的负载均衡，同一分组的路由根据权重进行负载
+ 可以配置2个值，逗号分割，分别是分组和权重
+ WeightCalculatorWebFilter：启动时，根据Weight配置生成一个双层的Map，第一层是分组名称，第二层是路由id；请求到来时，生成一个0~1随机数，每个分组的选择一个路由ID
+ WeightRoutePredicateFactory：谓词过滤时，根据分组和路由ID进行过滤

# 过滤器
+ 配置写法和谓词相同，字符串写法：等号分割，第一部分对应过滤器工厂GatewayFilterFactory类名前缀，第二部分是参数
+ 过滤器用于修改请求和响应

AddRequestHeader

+ 添加请求头，后端可以获取到
+ 请求头的值支持从uriVariables中动态获取

StripPrefix

+ 只有一个整数值n，将请求的路径按"/"分割后，去除前缀n个

# 限流
# 跨域
```bash
spring.cloud.gateway.globalcors:
  cors-configurations:
    '[/**]': #跨域的uriPattern
      allowedHeaders: "*"
      allowedOrigins: "*"
      allowedMethods:
        - POST
        - OPTIONS
        - GET
```

+ 服务端通过请求头Origin和请求url的scheme、host、port是否相同来判断是否为跨域请求，只要有一个不同则为跨域请求
+ 必须有跨域配置，并且请求的uri和跨域配置的uriPattern匹配，网关才会判断是否跨域，如果跨域，通过跨域配置中允许跨域的请求头、来源、请求方法和实际请求的请求头、来源、请求方法是否匹配，如果都匹配，则运行跨域访问，否则返回403Forbiden
+ org.springframework.web.reactive.handler.AbstractHandlerMapping#getHandler
+ org.springframework.web.cors.reactive.DefaultCorsProcessor#process

# 自动生成路由
+ 支持通过服务发现获取服务ID，自动根据服务ID生成路由配置。默认的路由配置的uri是lb://serviceId，谓词是/serviceId/**，过滤器是Rewritepath将serviceId去掉

# 全局过滤器
ReactiveLoadBalancerClientFilter

+ 处理带lb scheme的路由URI，先通过ServiceInstanceListSupplier根据服务名称获取服务实例，再通过ReactorLoadBalancer实例负载均衡

RouteToRequestUrlFilter

+ 做2件事情：1、支持2层scheme，将外层scheme保存到GATEWAY_SCHEME_PREFIX_ATTR，然后去除。2、使用内层sheme、host、port替换实际请求的uri，从而实现转发

