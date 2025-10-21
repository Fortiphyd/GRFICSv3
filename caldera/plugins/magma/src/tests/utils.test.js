import { cartesian } from '../utils/utils';

describe('cartesian function', () => {
  it('should return an empty array when input is empty', () => {
    expect(cartesian([])).toEqual([]);
  });

  it('should return the correct cartesian product for non-empty arrays', () => {
    const input = [[1, 2], [3, 4]];
    const expectedOutput = [
      [1, 3],
      [1, 4],
      [2, 3],
      [2, 4]
    ];
    expect(cartesian(input)).toEqual(expectedOutput);
  });

  it('should allow arrays with empty sub-arrays', () => {
    const input = [[1, 2], [], [3, 4]];
    const expectedOutput = [
      [1, 3],
      [1, 4],
      [2, 3],
      [2, 4]
    ];
    expect(cartesian(input)).toEqual(expectedOutput);
  });

  it('should handle arrays with single elements', () => {
    const input = [[1], [2], [3]];
    const expectedOutput = [
      [1, 2, 3]
    ];
    expect(cartesian(input)).toEqual(expectedOutput);
  });
});
