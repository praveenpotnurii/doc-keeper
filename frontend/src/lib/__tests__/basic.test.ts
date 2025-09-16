// Basic functionality tests
describe('Basic Functionality', () => {
  test('JavaScript array methods work', () => {
    const arr = [1, 2, 3, 4, 5];
    expect(arr.filter(x => x > 3)).toEqual([4, 5]);
    expect(arr.map(x => x * 2)).toEqual([2, 4, 6, 8, 10]);
    expect(arr.reduce((a, b) => a + b, 0)).toBe(15);
  });

  test('JavaScript object methods work', () => {
    const obj = { a: 1, b: 2, c: 3 };
    expect(Object.keys(obj)).toEqual(['a', 'b', 'c']);
    expect(Object.values(obj)).toEqual([1, 2, 3]);
    expect(Object.entries(obj)).toEqual([['a', 1], ['b', 2], ['c', 3]]);
  });

  test('Promises and async/await work', async () => {
    const promise = Promise.resolve(42);
    const result = await promise;
    expect(result).toBe(42);
  });

  test('Regular expressions work', () => {
    const email = 'test@example.com';
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    expect(emailRegex.test(email)).toBe(true);
    expect(emailRegex.test('invalid-email')).toBe(false);
  });

  test('Date functionality works', () => {
    const date = new Date('2024-01-01');
    expect(date.getFullYear()).toBe(2024);
    expect(date.getMonth()).toBe(0); // January is 0
    expect(date.getDate()).toBe(1);
  });
});