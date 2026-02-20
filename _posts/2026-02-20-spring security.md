---
tags:
    - 后端
    - spring
---

# 过滤器
![画板](/assets/images/1676340391327-7b9a2ce0-7bb6-4085-870e-937899f1eda3.jpeg)

servlet容器启动时，会执行servlet容器初始化器ServletContainerInitializer的onStartup，它执行servlet上下文初始化器ServletContextInitializer的onStartup，后者有一个实现类RegistrationBean，可以用来向servlet上下文注册组件，比如过滤器由派生类<font style="color:#DF2A3F;">AbstractFilterRegistrationBean</font>来注册，注册步骤：

1. 创建过滤器：执行getFilter抽象方法
2. 配置过滤器：配置dispatcherTypes、拦截的url和servletName

dispatcherType通常用来区分普通请求、转发的请求(forward)、错误页面请求、异步请求，过滤器生命周期：

1. init：创建和配置完过滤器后，执行init方法，<font style="color:#DF2A3F;">在容器启动时执行</font>
2. doFilter：根据dispatcherType和拦截的url、servletName找到对应的过滤器，执行doFilter，<font style="color:#DF2A3F;">每次请求到来时执行</font>。

DelegatingFilterProxyRegistrationBean：方便和spring整合，它是ApplicationContextAware，实际注册的是DelegatingFilterProxy对象，后者doFilter执行时可以根据过滤器的beanName找到真正执行业务逻辑的过滤器，并执行。DelegatingFilterProxy默认不会执行目标过滤器的init方法，因为与spring整合了，过滤器本身是spring bean，初始化逻辑由spring的初始化方法执行(@PostConstruct或afterpropertiesSet)

# 基本组件
## 配置类
![画板](https://cdn.nlark.com/yuque/0/2023/jpeg/22011769/1676364163869-951c6291-4f7a-4b57-9bf0-eaa2bce4cf21.jpeg)

+ springSecurityFilterChain：自动配置类SecurityAutoConfiguration通过@Import引入了WebSecurityEnablerConfiguration，WebSecurityEnablerConfiguration通过@EnableWebSecurity引入了WebSecurityConfiguration，配置类WebSecurityConfiguration定义了beanName是springSecurityFilterChain的过滤器，而SecurityFilterAutoConfiguration引入的DelegatingFilterProxyRegistrationBean向web容器注册的代理过滤器代理的过滤器的beanName就是springSecurityFilterChain。
+ AuthenticationConfiguration是身份验证相关组件的配置类

## springSecurityFilterChain
![画板](https://cdn.nlark.com/yuque/0/2023/jpeg/22011769/1676352209896-2d29f0b2-675f-4e37-ab5d-77ec10bbeb79.jpeg)

spring security的扩展组件由建造者SecurityBuilder的build创建，一般不会直接实现SecurityBuilder，而是通过实现配置者SecurityConfigurer来扩展组件，它提供了init和configure方法，用来初始化和配置建造者，然后再由建造者完成最后的组件创建和保存。AbstractSecurityBuilder缓存了组件，确保组件是单例的，AbstractConfiguredSecurityBuilder支持向建造者中添加和移除多个配置者，执行构建的逻辑：

1. 执行所有配置者的init，<font style="color:#DF2A3F;">和configure的区别：init可能向建造者添加新的配置者，从而再configure时执行新的配置者的configure</font>
2. 执行所有配置者的configure
3. 执行AbstractConfiguredSecurityBuilder的抽象方法performBuild

实现类：

+ WebSecurityConfigurerAdapter：是配置者的工具父类，用户可以继承它来实现配置者。<font style="color:#DF2A3F;">是WebSecurity的配置者，会创建和配置HttpSecurity，并且将它添加到WebSecurity</font>，主要逻辑通过init实现，它的init方法：1、创建了HttpSecurity，向HttpSecurity添加了默认的配置者。2、调用configure(HttpSecurity)抽象方法，用户可以通过实现该方法来添加自定义配置者。3、向WebSecurity添加了HttpSecurity。4、设置WebSecurity的postBuildAction
+ HttpSecurity：<font style="color:#DF2A3F;">创建的组件是过滤器链SecurityFilterChain</font><font style="color:#000000;">，默认是</font>DefaultSecurityFilterChain。它的配置者向它添加了多个过滤器，performBuild使用这些这些过滤器创建DefaultSecurityFilterChain
+ WebSecurity：<font style="color:#DF2A3F;">创建的组件是过滤器Filter</font>，它在创建时添加了用户定义的配置者bean，比如WebSecurityConfigurerAdapter的实现类，如果用户没有定义配置者，默认是WebSecurityConfigurerAdapter。它<font style="color:#DF2A3F;">可以添加多个组件是过滤器链的建造者</font>，在performBuild时，执行这些建造者的build方法得到多个过滤器链，根据这些过滤器链创建<font style="color:#DF2A3F;">FilterChainProxy，也就是最终要得到的过滤器实现类springSecurityFilterChain</font><font style="color:#000000;">。创建完FilterChainProxy后，执行</font>postBuildAction

```java
public interface SecurityBuilder<O> {
	O build() throws Exception; 
}
public interface SecurityConfigurer<O, B extends SecurityBuilder<O>> { 
	void init(B builder) throws Exception; 
	void configure(B builder) throws Exception; 
}
//AbstractConfiguredSecurityBuilder
protected final O doBuild() throws Exception {
    synchronized (this.configurers) { 
    //执行配置者的init
        init();  
    //执行配置者的configure
        configure(); 
        O result = performBuild(); 
        return result;
    }
}
//WebSecurityConfigurerAdapter
public void init(WebSecurity web) throws Exception {
    HttpSecurity http = getHttp();
    web.addSecurityFilterChainBuilder(http).postBuildAction(() -> {
        FilterSecurityInterceptor securityInterceptor = http.getSharedObject(FilterSecurityInterceptor.class);
        web.securityInterceptor(securityInterceptor);
    });
}
//HttpSecurity
protected DefaultSecurityFilterChain performBuild() {
    this.filters.sort(OrderComparator.INSTANCE);
    List<Filter> sortedFilters = new ArrayList<>(this.filters.size());
    for (Filter filter : this.filters) {
        sortedFilters.add(((OrderedFilter) filter).filter);
    }
    return new DefaultSecurityFilterChain(this.requestMatcher, sortedFilters);
}
//WebSecurity
protected Filter performBuild() throws Exception { 
    int chainSize = this.ignoredRequests.size() + this.securityFilterChainBuilders.size();
    for (SecurityBuilder<? extends SecurityFilterChain> securityFilterChainBuilder : this.securityFilterChainBuilders) {
        SecurityFilterChain securityFilterChain = securityFilterChainBuilder.build();
        securityFilterChains.add(securityFilterChain); 
    } 
    FilterChainProxy filterChainProxy = new FilterChainProxy(securityFilterChains); 
    return result;
}
```

其它组件：

+ ObjectPostProcessor：对象后置处理器，用于跟spring整合，比如实现类AutowireBeanFactoryObjectPostProcessor：1、会执行已创建的对象的spring初始化方法(XXAware、bean的后置处理器的初始化前后方法、afterPropertySet)。2、注入bean，比如@Autowire注解注入。3、支持DisposableBean和SmartInitializingSingleton

FilterChainProxy保存了多个过滤器链，比如HttpSecurity创建的DefaultSecurityFilterChain，doFilter执行流程：

1. 使用StrictHttpFirewall包装请求和响应，包装对象实现了对请求和响应的校验，请求：可以根据主机名称和http方法进行拦截，url、请求头、参数中不能包含一些非法字符；响应：校验了响应头和cookie，cookie的名称、值、路径、域名中不能有换行符
2. 依次执行SecurityFilterChain.matches，选择第一个匹配成功的过滤器链，执行这个链。DefaultSecurityFilterChain的matches会执行requestMatcher.matches，由HttpSecurity配置请求匹配器，通配符匹配antMatcher和正则匹配regexMatcher匹配的是包括contextPath的路径(不包括域名)，mvcMatcher匹配的是去除contextPath后的路径。只对匹配通过的使用spring security过滤器

# spring security过滤器
## 身份验证(Authentication)
### AuthenticationManager
![画板](https://cdn.nlark.com/yuque/0/2023/jpeg/22011769/1676450524182-da025117-565c-4662-9f70-854677859641.jpeg)

**AuthenticationConfiguration创建的AuthenticationManager**：AuthenticationConfiguration定义了DefaultPasswordEncoderAuthenticationManagerBuilder bean，它是AuthenticationManagerBuilder的子类，AuthenticationManagerBuilder是AuthenticationManager的建造者，创建前添加了配置者GlobalAuthenticationConfigurerAdapter，配置者实现类：

+ InitializeAuthenticationProviderBeanManagerConfigurer：支持AuthenticationProvider实现类用bean的方式定义，将该类型的bean添加到AuthenticationManagerBuilder中
+ InitializeUserDetailsBeanManagerConfigurer：支持UserDetailsService、PasswordEncoder用bean的方式定义，将它们添加到DaoAuthenticationProvider，然后将DaoAuthenticationProvider添加到AuthenticationManagerBuilder

**AuthenticationManager.authenticate验证逻辑**：AuthenticationManagerBuilder创建的AuthenticationManager实现类是ProviderManager，它对应多个AuthenticationProvider和一个父级的AuthenticationManager

1.  执行当前的其中的supports为true的AuthenticationProvider的authenticate，使用第一个不为null的返回值
2. 子级的AuthenticationManager返回null时，才会调用父级的AuthenticationManager。
3. 验证失败，抛出AuthenticationException

**WebSecurityConfigurerAdapter创建的AuthenticationManager**：WebSecurityConfigurerAdapter创建的是DefaultPasswordEncoderAuthenticationManagerBuilder，它是AuthenticationManagerBuilder的子类，创建的AuthenticationManager的父级建造者是AuthenticationConfiguration创建的AuthenticationManager，这个建造者会传入HttpSecurity，当通过HttpSecurity配置AuthenticationProvider、UserDetailsService、PasswordEncoder时，实际配置的是这个AuthenticationManager。

**小结**：<font style="color:#DF2A3F;">会创建2个AuthenticationManager，它们是父子级的关系，子级的内部组件AuthenticationProvider、UserDetailsService、PasswordEncoder通过HttpSecurity配置，父级通过bean的方式配置，子级优先级更高</font><font style="color:#000000;">。</font>

```java
//AuthenticationConfiguration
public AuthenticationManager getAuthenticationManager() throws Exception { 
    AuthenticationManagerBuilder authBuilder = this.applicationContext.getBean(AuthenticationManagerBuilder.class); 
//GlobalAuthenticationConfigurerAdapter支持bean的方式定义AuthenticationProvider、UserDetailsService、PasswordEncoder
    for (GlobalAuthenticationConfigurerAdapter config : this.globalAuthConfigurers) {
        authBuilder.apply(config);
    }
    this.authenticationManager = authBuilder.build(); 
    return this.authenticationManager;
}
//AuthenticationManagerBuilder创建的是ProviderManager，并且传入authenticationProviders和父级的AuthenticationManager
protected ProviderManager performBuild() throws Exception { 
    ProviderManager providerManager = new ProviderManager(this.authenticationProviders,
            this.parentAuthenticationManager); 
    return providerManager;
}
//WebSecurityConfigurerAdapter
protected final HttpSecurity getHttp() throws Exception {  
    //获取AuthenticationConfiguration创建的的AuthenticationManager
    AuthenticationManager authenticationManager = authenticationManager();
//将自己的authenticationBuilder父级设为它
    this.authenticationBuilder.parentAuthenticationManager(authenticationManager);
//将子级的authenticationBuilder传入HttpSecurity
	this.http = new HttpSecurity(this.objectPostProcessor, this.authenticationBuilder, sharedObjects);
...
}
//HttpSecurity，加到SharedObject，配置方法实际上配的是子级的AuthenticationManagerBuilder
public HttpSecurity(ObjectPostProcessor<Object> objectPostProcessor,
			AuthenticationManagerBuilder authenticationBuilder, Map<Class<?>, Object> sharedObjects) { 
    setSharedObject(AuthenticationManagerBuilder.class, authenticationBuilder); 
} 
public HttpSecurity authenticationProvider(AuthenticationProvider authenticationProvider) {
    getAuthenticationRegistry().authenticationProvider(authenticationProvider);
    return this;
} 
public HttpSecurity userDetailsService(UserDetailsService userDetailsService) throws Exception {
    getAuthenticationRegistry().userDetailsService(userDetailsService);
    return this;
} 
private AuthenticationManagerBuilder getAuthenticationRegistry() {
    return getSharedObject(AuthenticationManagerBuilder.class);
}
```

### DaoAuthenticationProvider
1. 调用UserDetailsService#loadUserByUsername根据用户名获取用户对象UserDetails，比如从用户表查询，查询不到用户时应抛出UsernameNotFoundException
2. 验证用户是否锁住、是否启用、是否过期，如果有则抛出异常
3. 调用passwordEncoder验证用户的密码是否匹配
4. 判断用户密码是否过期
5. 验证通过，返回，否则抛出AuthenticationException

### Bcypt
bcypt是hash加密算法，用于加密保存用户的密码，hash算法是单向的，相比于其它hash算法(MD5、SHA1、SHA2、SHA3)，它加密时增加了随机的盐值，相同明文多次加密会得到不同密文，并且可以指定迭代轮次(2^4~2^31)来防御彩虹表攻击。

密文组成：$2<a/b/x/y>$[cost]$[22 character salt][31 character hash]版本号+迭代轮次+盐值+hash值

+ 版本号：2a、2x/2y、2b，后一个是前面的bug解决版本，允许加密任意utf8编码的字符串。
+ 迭代轮次：是初始化并生成P、S后，对明文和盐值加密的次数。
+ 盐值：是16字节的随机值经过base64得到的22个字符，每次加密都会重新生成，从而每次加密算出的hash值不同。
+ hash：明文、盐值、迭代轮次相同时，计算出的hash相同。3+7*4=31，计算出的hash是24B，取前23B的base64

明文和密文匹配逻辑：使用明文+密文中的盐值+密文中的迭代轮次计算出密文，再和数据库中的密文比对

彩虹表攻击：要破解hash加密，字典法先计算出大量的明文的密文，将它们保存起来，空间占用高；穷举法CPU占用高，耗时长。彩虹表采用折中方案，只保存了链条中的首尾值，找出匹配的链条后，再根据第一个值还原链条，直到找到密文。链条的生成：用大量随机的明文依次使用n次H函数和R函数，H是要破解的hash算法，R是约减函数，值域与H的定义域相同，为了减小碰撞，每次迭代可以使用不同的R，链条中实际上是对明文使用H，对密文使用R，只保存明文和最后一个值。破解逻辑：将密文使用R得到的值，与存储的值进行比对，如果比对不上则再使用H和R，直到查询出匹配的值，或者迭代次数超过链条长度，破解失败，查询出匹配的值后，使用对应的明文还原链条，直到找到一个明文的H函数值是要破解的密文。

为什么能防御彩虹表：1、Bcrypt每次生成的密文都不同，还原链条时不能得到明文。2、可以指定迭代轮次增加计算成本，从而增加生成彩虹表的成本

### UsernamePasswordAuthenticationFilter
![画板](https://cdn.nlark.com/yuque/0/2023/jpeg/22011769/1676465017202-39b58514-c5ad-457d-a15c-ab5b99f6b674.jpeg)

该过滤器实现了用户名密码的登录验证逻辑，通过FormLoginConfigurer的configure加入，它通过AuthenticationManager实现用户名密码的验证

验证逻辑：

1. 判断请求是否需要验证，比如请求的url是登录url时，才会进行登录验证
2. 从请求的查询串或表单中获取用户名密码
3. 执行AuthenticationManager的authenticate验证，它验证失败抛出AuthenticationException
4. 验证失败执行rememberMeServices.loginFail和failureHandler.onAuthenticationFailure，将请求、响应、AuthenticationException异常传给AuthenticationFailureHandler，让它根据异常的具体类型进行处理
5. 验证成功，使用SecurityContextHolderStrategy创建SecurityContext，将Authentication保存进SecurityContext，执行sessionStrategy.onAuthentication、rememberMeServices.loginSuccess、successHandler.onAuthenticationSuccess

### AuthenticationSuccessHandler
![画板](https://cdn.nlark.com/yuque/0/2023/jpeg/22011769/1676452470472-8b532525-c68f-4ef6-8336-b0c2324c6d4a.jpeg)

验证成功执行onAuthenticationSuccess的处理器，<font style="color:#DF2A3F;">前后端分离的需要自定义实现，返回json</font>

+ AbstractAuthenticationTargetUrlRequestHandler：发送重定向响应的工具父类，可以配置从请求的某个参数获取重定向url，默认重定向路径是/
+ SimpleUrlAuthenticationSuccessHandler：是AbstractAuthenticationTargetUrlRequestHandler实现类
+ SavedRequestAwareAuthenticationSuccessHandler：<font style="color:#DF2A3F;">默认配置</font>，通过HttpSessionRequestCache在会话中记录了上次验证失败的请求，验证通过重定向到上次验证失败的请求
+ ForwardAuthenticationSuccessHandler：服务端内部转发到指定的url，转发时会执行DispatcherType为FORWARD的过滤器和servlet，spring security过滤器securityFitlerChain默认是REQUEST，所以不会执行。可以自定义实现转发的url，<font style="color:#DF2A3F;">相比与直接实现 AuthenticationSuccessHandler接口，转发的方式可以通过HandlerMethod实现登录成功的逻辑，比如记录登录时间和ip、返回用户信息</font>。

### AuthenticationFailureHandler
默认实现是SimpleUrlAuthenticationFailureHandler，它的默认实现是返回401验证错误，另外还可以<font style="color:#DF2A3F;">转发到指定url，由HandlerMethod处理，比如记录验证错误次数，失败次数过多锁定账户等</font>。

### SecurityContextHolderStrategy
![画板](https://cdn.nlark.com/yuque/0/2023/jpeg/22011769/1676465603955-93fb5c92-072c-47c1-9624-f674231adb5f.jpeg)



```java
public interface SecurityContextHolderStrategy { 
	void clearContext(); 
	SecurityContext getContext(); 
	void setContext(SecurityContext context); 
	SecurityContext createEmptyContext(); 
}
```

