import java.util.ArrayList;
import java.util.List;
import java.util.Scanner;

/**
 * A class to generate and manage Fibonacci sequence operations.
 * Provides methods to compute the Fibonacci sequence up to the nth number.
 */
public class Fibonacci {
    /** Maximum safe index for Fibonacci numbers to prevent long overflow. */
    private static final int MAX_SAFE_FIBONACCI_INDEX = 93;

    /**
     * Generates the first n numbers in the Fibonacci sequence.
     *
     * @param n the number of Fibonacci numbers to generate
     * @return a List containing the first n Fibonacci numbers
     * @throws IllegalArgumentException if n is negative or exceeds safe range
     */
    public static List<Long> generateFibonacci(int n) {
        if (n < 0) {
            throw new IllegalArgumentException("Input must be non-negative");
        }
        if (n > MAX_SAFE_FIBONACCI_INDEX) {
            throw new IllegalArgumentException(
                "Input exceeds safe range (max: " + MAX_SAFE_FIBONACCI_INDEX + ") due to long overflow"
            );
        }

        List<Long> fib = new ArrayList<>();
        if (n == 0) return fib;
        fib.add(0L);
        if (n == 1) return fib;
        fib.add(1L);

        for (int i = 2; i < n; i++) {
            fib.add(fib.get(i - 1) + fib.get(i - 2));
        }
        return fib;
    }

    /**
     * Reads an integer input from the user via console.
     *
     * @param scanner the Scanner object to read input
     * @return the integer input provided by the user
     * @throws IllegalArgumentException if the input is not a valid integer
     */
    private static int readUserInput(Scanner scanner) {
        if (!scanner.hasNextInt()) {
            throw new IllegalArgumentException("Invalid input: please enter a valid integer");
        }
        return scanner.nextInt();
    }

    /**
     * Prints the Fibonacci sequence to the console in a formatted manner.
     *
     * @param fib the List containing the Fibonacci sequence
     */
    private static void printFibonacciSequence(List<Long> fib) {
        System.out.print("Fibonacci sequence (" + fib.size() + " numbers): ");
        if (fib.isEmpty()) {
            System.out.println("[]");
            return;
        }
        for (int i = 0; i < fib.size(); i++) {
            System.out.print(fib.get(i));
            if (i < fib.size() - 1) {
                System.out.print(", ");
            }
        }
        System.out.println();
    }

    /**
     * Main method to demonstrate Fibonacci sequence generation with user input.
     *
     * @param args command-line arguments (not used)
     */
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        try {
            System.out.print("Enter the number of Fibonacci numbers to generate: ");
            int n = readUserInput(scanner);
            List<Long> result = generateFibonacci(n);
            printFibonacciSequence(result);
        } catch (IllegalArgumentException e) {
            System.err.println("Error: " + e.getMessage());
            System.exit(1);
        } finally {
            scanner.close();
        }
    }
}