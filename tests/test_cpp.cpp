#include <iostream>
#include <vector>
#include <stdexcept>
#include <limits>

// C++ Fibonacci
std::vector<long long> fibonacci(int n) {
    /**
     * Generate the first n numbers in the Fibonacci sequence.
     * @param n Number of Fibonacci numbers to generate.
     * @return Vector containing the first n Fibonacci numbers.
     * @throws std::invalid_argument if n is negative or too large.
     */
    // Validate input
    if (n < 0) {
        throw std::invalid_argument("Input must be non-negative");
    }
    // Check for potential overflow (limit to prevent vector size issues)
    if (n > 93) { // long long can safely store Fibonacci numbers up to F(93)
        throw std::invalid_argument("Input too large; exceeds safe Fibonacci range");
    }

    std::vector<long long> fib;
    // Handle edge cases
    if (n == 0) return fib;
    fib.push_back(0);
    if (n == 1) return fib;
    fib.push_back(1);

    // Generate Fibonacci sequence
    for (int i = 2; i < n; ++i) {
        fib.push_back(fib[i-1] + fib[i-2]);
    }
    return fib;
}

// Example usage with user input
int main() {
    int n;
    std::cout << "Enter the number of Fibonacci numbers to generate: ";
    if (!(std::cin >> n)) {
        std::cerr << "Error: Invalid input, please enter an integer" << std::endl;
        return 1;
    }

    try {
        std::vector<long long> result = fibonacci(n);
        std::cout << "Fibonacci sequence (" << result.size() << " numbers): ";
        for (long long num : result) {
            std::cout << num << " ";
        }
        std::cout << std::endl;
    } catch (const std::invalid_argument& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
    return 0;
}