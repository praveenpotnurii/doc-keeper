import { cn } from '../utils';

describe('Utils', () => {
  test('cn combines class names correctly', () => {
    const result = cn('class1', 'class2');
    expect(result).toContain('class1');
    expect(result).toContain('class2');
  });

  test('cn handles conditional classes', () => {
    const result = cn('base', true && 'conditional', false && 'hidden');
    expect(result).toContain('base');
    expect(result).toContain('conditional');
    expect(result).not.toContain('hidden');
  });

  test('cn handles empty/undefined inputs', () => {
    const result = cn('', undefined, null, 'valid');
    expect(result).toContain('valid');
    expect(result).not.toContain('undefined');
    expect(result).not.toContain('null');
  });
});