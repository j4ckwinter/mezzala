from collections.abc import Sequence

BLOCKED = 1e12


def min_cost_assignment(cost: Sequence[Sequence[float]]) -> list[int]:
    rows = len(cost)
    columns = len(cost[0]) if rows else 0
    if rows > columns:
        raise ValueError("min_cost_assignment needs at least as many columns as rows")
    row_potential = [0.0] * (rows + 1)
    column_potential = [0.0] * (columns + 1)
    owner = [0] * (columns + 1)
    previous = [0] * (columns + 1)
    for row in range(1, rows + 1):
        owner[0] = row
        column = 0
        slack = [float("inf")] * (columns + 1)
        visited = [False] * (columns + 1)
        while True:
            visited[column] = True
            current_row = owner[column]
            delta = float("inf")
            next_column = 0
            for candidate in range(1, columns + 1):
                if visited[candidate]:
                    continue
                reduced = (
                    cost[current_row - 1][candidate - 1] - row_potential[current_row] - column_potential[candidate]
                )
                if reduced < slack[candidate]:
                    slack[candidate] = reduced
                    previous[candidate] = column
                if slack[candidate] < delta:
                    delta = slack[candidate]
                    next_column = candidate
            for candidate in range(columns + 1):
                if visited[candidate]:
                    row_potential[owner[candidate]] += delta
                    column_potential[candidate] -= delta
                else:
                    slack[candidate] -= delta
            column = next_column
            if owner[column] == 0:
                break
        while column:
            prior = previous[column]
            owner[column] = owner[prior]
            column = prior
    chosen = [0] * rows
    for column in range(1, columns + 1):
        if owner[column]:
            chosen[owner[column] - 1] = column - 1
    return chosen
