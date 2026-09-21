from fractions import Fraction


def smith_normal_form(
    source: list[list[int]], row_count: int
) -> tuple[tuple[int, ...], tuple[tuple[int, ...], ...]]:
    """Return D's nonzero diagonal and U where U * source * V = D."""

    column_count = len(source[0]) if source else 0
    matrix = [row[:] for row in source] if source else [[] for _ in range(row_count)]
    transform = [[int(i == j) for j in range(row_count)] for i in range(row_count)]

    def swap_rows(first: int, second: int) -> None:
        matrix[first], matrix[second] = matrix[second], matrix[first]
        transform[first], transform[second] = transform[second], transform[first]

    def add_row(target: int, source_row: int, multiple: int) -> None:
        matrix[target] = [
            value + multiple * other
            for value, other in zip(matrix[target], matrix[source_row], strict=True)
        ]
        transform[target] = [
            value + multiple * other
            for value, other in zip(transform[target], transform[source_row], strict=True)
        ]

    def swap_columns(first: int, second: int) -> None:
        for row in matrix:
            row[first], row[second] = row[second], row[first]

    pivot = 0
    while pivot < row_count and pivot < column_count:
        locations = [
            (abs(matrix[row][column]), row, column)
            for row in range(pivot, row_count)
            for column in range(pivot, column_count)
            if matrix[row][column]
        ]
        if not locations:
            break
        _, row, column = min(locations)
        swap_rows(pivot, row)
        swap_columns(pivot, column)
        while True:
            changed = False
            for row in range(pivot + 1, row_count):
                if matrix[row][pivot]:
                    quotient = matrix[row][pivot] // matrix[pivot][pivot]
                    add_row(row, pivot, -quotient)
                    if matrix[row][pivot]:
                        swap_rows(row, pivot)
                    changed = True
                    break
            if changed:
                continue
            for column in range(pivot + 1, column_count):
                if matrix[pivot][column]:
                    quotient = matrix[pivot][column] // matrix[pivot][pivot]
                    for row in matrix:
                        row[column] -= quotient * row[pivot]
                    if matrix[pivot][column]:
                        swap_columns(column, pivot)
                    changed = True
                    break
            if changed:
                continue
            offender = next(
                (
                    (row, column)
                    for row in range(pivot + 1, row_count)
                    for column in range(pivot + 1, column_count)
                    if matrix[row][column] % matrix[pivot][pivot]
                ),
                None,
            )
            if offender is None:
                break
            add_row(pivot, offender[0], 1)
        if matrix[pivot][pivot] < 0:
            add_row(pivot, pivot, -2)
        pivot += 1
    diagonal = tuple(
        abs(matrix[index][index])
        for index in range(min(row_count, column_count))
        if matrix[index][index]
    )
    return diagonal, tuple(tuple(row) for row in transform)


def unimodular_inverse(matrix: tuple[tuple[int, ...], ...]) -> tuple[tuple[int, ...], ...]:
    size = len(matrix)
    augmented = [
        [*(Fraction(value) for value in row), *(Fraction(int(i == j)) for j in range(size))]
        for i, row in enumerate(matrix)
    ]
    for column in range(size):
        pivot = next(row for row in range(column, size) if augmented[row][column])
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row != column and augmented[row][column]:
                multiple = augmented[row][column]
                augmented[row] = [
                    value - multiple * other
                    for value, other in zip(augmented[row], augmented[column], strict=True)
                ]
    return tuple(tuple(int(value) for value in row[size:]) for row in augmented)
