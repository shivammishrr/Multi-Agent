# Python Fibonacci
def fibonacci(n):
    """
    Generate the first n numbers in the Fibonacci sequence.
    Args:
        n (int): Number of Fibonacci numbers to generate.
    Returns:
        list: List containing the first n Fibonacci numbers.
    """
    # Handle edge cases
    if not isinstance(n, int):
        raise TypeError("Input must be an integer")
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    
    # Initialize the sequence
    fib = [0, 1]
    # Generate subsequent Fibonacci numbers
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])
    return fib

# Example usage
# if __name__ == "__main__":
try:
    print(fibonacci(10))  # Output: [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
except TypeError as e:
    print(f"Error: {e}")