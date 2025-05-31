#include <stdio.h>
#include <stdlib.h>
#include <limits.h>

// C Fibonacci
long long* fibonacci(int n, int* size) {
    /**
     * Generate the first n numbers in the Fibonacci sequence.
     * @param n Number of Fibonacci numbers to generate.
     * @param size Pointer to store the size of the returned array.
     * @return Pointer to array containing the first n Fibonacci numbers.
     *         Returns NULL on error. Caller must free the memory.
     */
    // Validate input
    if (n < 0) {
        *size = 0;
        fprintf(stderr, "Error: Input must be non-negative\n");
        return NULL;
    }
    if (n > 93) { // long long can safely store Fibonacci numbers up to F(93)
        *size = 0;
        fprintf(stderr, "Error: Input too large; exceeds safe Fibonacci range\n");
        return NULL;
    }

    // Set output size
    *size = n;
    // Handle edge case: n == 0
    if (n == 0) {
        return (long long*)malloc(0); // Allocate empty array for consistency
    }

    // Allocate memory
    long long* fib = (long long*)malloc(n * sizeof(long long));
    if (fib == NULL) {
        *size = 0;
        fprintf(stderr, "Error: Memory allocation failed\n");
        return NULL;
    }

    // Initialize first elements
    fib[0] = 0;
    if (n == 1) return fib;
    fib[1] = 1;

    // Generate Fibonacci sequence
    for (int i = 2; i < n; ++i) {
        fib[i] = fib[i-1] + fib[i-2];
    }
    return fib;
}

// Example usage with direct execution
int main() {
    int n = 10; // Directly use 10 as the number of Fibonacci numbers to generate
    
    int size;
    long long* result = fibonacci(n, &size);
    if (result == NULL) {
        return 1; // Error message already printed by fibonacci
    }

    printf("Fibonacci sequence (%d numbers): ", size);
    for (int i = 0; i < size; ++i) {
        printf("%lld ", result[i]);
    }
    printf("\n");

    free(result); // Free allocated memory
    return 0;
}