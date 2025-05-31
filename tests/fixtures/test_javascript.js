// JavaScript Fibonacci
function fibonacci(n) {
    /**
     * Generate the first n numbers in the Fibonacci sequence.
     * @param {number} n - Number of Fibonacci numbers to generate.
     * @returns {number[]} - Array containing the first n Fibonacci numbers.
     */
    // Handle edge cases
    if (!Number.isInteger(n)) {
        throw new TypeError("Input must be an integer");
    }
    if (n <= 0) return [];
    if (n === 1) return [0];
    
    // Initialize the sequence
    let fib = [0, 1];
    // Generate subsequent Fibonacci numbers
    for (let i = 2; i < n; i++) {
        fib.push(fib[i-1] + fib[i-2]);
    }
    return fib;
}

// Example usage
try {
    console.log(fibonacci(10)); // Output: [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
} catch (error) {
    console.error(`Error: ${error.message}`);
}