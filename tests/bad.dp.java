import java.util.Scanner;

public class BadDP {

    static int fib(int n) {
        if (n <= 1)
            return n;
        return fib(n - 1) + fib(n - 2);
    }

    static int knapsack(int W, int wt[], int val[], int n) {

        if (n == 0 || W == 0)
            return 0;

        if (wt[n - 1] > W)
            return knapsack(W, wt, val, n - 1);

        return Math.max(
            val[n - 1] + knapsack(W - wt[n - 1], wt, val, n - 1),
            knapsack(W, wt, val, n - 1)
        );
    }

    public static void main(String[] args) {

        Scanner sc = new Scanner(System.in);

        System.out.println("Enter Fibonacci Number:");

        int n = sc.nextInt();

        System.out.println(fib(n));

        int[] wt = {1, 3, 4, 5};
        int[] val = {1, 4, 5, 7};

        System.out.println(
            knapsack(7, wt, val, wt.length)
        );

        sc.close();
    }
}