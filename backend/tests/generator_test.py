def count(n):
    print("开始执行")
    for i in range(n):
        yield i
    print("执行结束")

for i in count(5):
    print(i)
gen=count(3)
print(next(gen))
print(next(gen))
print(next(gen))


