class FibonacciIterative:
    def __init__(self, n):
        self.n = n

    def fibonacci_series(self):
        fib_sequence = []
        first, second = 0, 1
        for _ in range(self.n):
            fib_sequence.append(first)
            first, second = second, first + second
        return fib_sequence

if __name__ == "__main__":
    n = 10
    fibonacci_iterative = FibonacciIterative(n)
    print("Fibonacci Series:", fibonacci_iterative.fibonacci_series())