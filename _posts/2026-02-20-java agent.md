---
tags:
    - 后端
---
## java agent
+ 有2种启动方式：静态启动和动态启动
+ 静态启动：需要通过-javaagent:的JVM参数指定agent jar，agent和目标进程运行在同一进程中，入口方法是premain，能对字节码做任意修改，使用场景：skywalking
+ 动态启动：不需要加JVM参数，agent运行在不同进程中，入口方法是agentmain，字节码操作限制较多，不能添加删除重命名字段和方法，能在方法添加代码，适用于系统诊断，比如arthas
+ [https://tech.meituan.com/2019/11/07/java-dynamic-debugging-technology.html](https://tech.meituan.com/2019/11/07/java-dynamic-debugging-technology.html)

### agentlib、agentpath、javaagent
+ [https://docs.oracle.com/javase/8/docs/platform/jvmti/jvmti.html](https://docs.oracle.com/javase/8/docs/platform/jvmti/jvmti.html)
+ 区别：agentlib用于根据库名称从jre/bin目录中加载本地库(dll或so)，agentpath根据库绝对路径加载本地库，javaagent根据jar包完整路径加载java库
+ 用法：-agentlib:libname[=options]。-agentpath:pathname[=options]。-javaagent:jarpath[=options]
+ -agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=5005，表示加载jre/bin/jdwp.dll，参数是transport=dt_socket,server=y,suspend=n,address=5005，远程调试
+ 解析参数：arguments.cpp中parse_each_vm_init_arg，保存到链表_agentList中(支持多个javaagent参数)，元素是AgentLibrary

```cpp
class AgentLibrary {
    char*           _name;//如果是本地库，则是动态库的名称，如果是jar包，固定是instrument
    char*           _options;//如果是jar包，包含了jar路径和参数，比如/home/cwj/java-agent-learn.jar=a,b
    bool            _is_absolute_path;//jar包固定为false
}
```

+ javaagent会使用${JAVA_HOME}/jre/lib/amd64/libinstrument.so动态链接库，找到其中的InvocationAdapter.c中的Agent_OnLoad方法

```cpp
void Threads::create_vm_init_agents() {
  extern struct JavaVM_ main_vm;
  AgentLibrary* agent;
  for (agent = Arguments::agents(); agent != NULL; agent = agent->next()) {
    OnLoadEntry_t  on_load_entry = lookup_agent_on_load(agent);//加载libinstrument.so动态链接库，并获取其中的Agent_OnLoad
    jint err = (*on_load_entry)(&main_vm, agent->options(), NULL);
}
```

Agent_OnLoad执行流程：

+ jvmtiEnv：jvmti的实现，通过JNIInvokeInterface_.GetEnv获取，jvmti负责创建JPLISAgent，注册JVM回调函数（JVM初始化、类加载等）
+ 创建JPLISAgent：每个该对象对应一个javaagent，其中保存了agent类、javaagent参数，注册VMInit回调函数为InvocationAdapter.eventHandlerVMInit
+ 读取agent jar中的Manifest的Premain-Class属性保存到JPLISAgent，将agent属性保存到JPLISAgent，将agent jar添加到SystemClassLoader类路径

```cpp
struct _JPLISAgent {
    JavaVM *                mJVM;                   /* handle to the JVM */
    JPLISEnvironment        mNormalEnvironment;     /* for every thing but retransform stuff */
    JPLISEnvironment        mRetransformEnvironment;/* for retransform stuff only */
    jobject                 mInstrumentationImpl;   /* InstrumentationImpl实例 */
    jmethodID               mPremainCaller;         /* InstrumentationImpl.loadClassAndCallPremain */
    jmethodID               mAgentmainCaller;       /* InstrumentationImpl.loadClassAndCallAgentmain */
    jmethodID               mTransform;             /* InstrumentationImpl.transform */
    jboolean                mRedefineAvailable;     /* cached answer to "does this agent support redefine" */
    jboolean                mRedefineAdded;         /* indicates if can_redefine_classes capability has been added */
    jboolean                mNativeMethodPrefixAvailable; /* cached answer to "does this agent support prefixing" */
    jboolean                mNativeMethodPrefixAdded;     /* indicates if can_set_native_method_prefix capability has been added */
    char const *            mAgentClassName;        /* agent class name */
    char const *            mOptionsString;         /* -javaagent options string */
};
```

InvocationAdapter.eventHandlerVMInit执行流程：

+ 使用systemclassLoader加载InstrumentationImpl类，创建实例，将实例的loadClassAndCallPremain方法ID保存到_JPLISAgent的mPremainCaller，实例本身保存到_JPLISAgent的mInstrumentationImpl。

```cpp
public class InstrumentationImpl implements Instrumentation {
    private final     long                    mNativeAgent;//是对应的_JPLISAgent的指针
}
```

+ 注册类加载回调函数：InvocationAdapter.eventHandlerClassFileLoadHook
+ 调用InstrumentationImpl.loadClassAndCallPremain，第一个参数是Premain-Class类名，第二个是agent参数。会先获取premain的2个参数的方法，如果获取不到则获取1个参数的，如果还获取不到，尝试依次获取从父类中继承的2个参数和1个参数的premain方法
+ getDeclaredMethod：能获取到当前类所有作用域的方法；getMethod：能获取到当前类和父类的public方法

### transformer
+ Instrumetation.addTransformer有2个重载方法，其中canRetransform=true时，manifest文件必须指定Can-Retransform-Classes=true
+ ClassFileTransformer在类加载、redefined、retransformed的时候被调用
+ Instrumetation.addTransformer将ClassFileTransformer添加到一个数组中，每个类在加载的时候都会执行Instrumetation.transform，调用ClassFileTransformer.transform。只有在addTransformer之后加载到类才会被对应Transformer拦截到，因为可以注册多个premain，而premain类也会被加载，先执行的premain可以拦截后面的premain类的加载

### retransform
+ Instrumetation.retransformClasses: 对已经加载的类，执行Transformer，对于canTransform=false的Transformer，会重用上一次transformer的执行结果，除非上一次没有执行；对于canTransform=true的Transformer，会重新执行它们，替换已经加载的类定义
+ retransform只能修改方法体，不能新增、删除字段和方法，不能重命名字段和方法名称、不能修改继承关系，如果这么做了，不会报错，但retransform不生效，仍使用第一次transformer的执行结果
+ retransform调用时，transformer接收到的字节码是最初没执行transform之前的字节码，而不是上一次转换的
+ retransform不会重新执行类clinit方法，clinit只会执行一次

### redefine
+ 和retransform一样,也只能修改方法体，不能新增、删除字段和方法，不能重命名字段和方法名称、不能修改继承关系。不会重新执行clinit
+ 和retransform的区别: redefineClasses方法的参数多了一个字节码参数，该参数会传进transform方法。都会触发transform方法，retransform的transform方法的入参接收到的字节码固定是transform之前的字节码，而redefine的入参字节码是redefineClasses方法传入的字节码



