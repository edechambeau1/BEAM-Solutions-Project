import heapq
import manifest_read
from collections import Counter, defaultdict
import copy
import time

DEBUG = False

MAX_BAY_Y = 10
SAIL_BAY_Y = 8
MAX_BAY_X = 12
MAX_BUFFER_Y = 4
MAX_BUFFER_X = 24
MAX_BUFFER_CONTAINERS = 96
testX = 5
testY = 4
testBufferX = 2
testBufferY = 2

def debugPrint(message):
    if DEBUG:
        print(message)

class BoardState:
    def __init__(self, bay, buffer, neededOff, currentOff, load, g, parent, moveDescription=None, movePositions=None):
        self.neededOff = neededOff
        self.currentOff = currentOff
        self.load = load
        self.bay = bay
        self.buffer = buffer
        self.g = g
        self.h = self.heuristic()
        self.parent = parent
        self.f = self.g + self.h
        self.depth = (parent.depth + 1) if parent else 0
        self.moveDescription = moveDescription
        self.movePositions = movePositions or []
        debugPrint(f"BoardState created: g={self.g}, h={self.h}, f={self.f}, depth={self.depth}, move: {self.moveDescription}")

    def heuristic(self):
        totalCost = 0

        for needed in self.neededOff:
            found = False
            for column, stack in self.bay.items():
                for row, container in enumerate(stack):
                    if container == needed:
                        position = (column + 1, row + 1)
                        offloadCost = abs(position[0]) + abs(position[1] - (testY + 1)) + 2
                        totalCost += offloadCost
                        found = True
                        break
                if found:
                    break

        iteration = 0
        for container in self.load:
            loadCost = 2 + abs(testY) + iteration
            totalCost += loadCost
            iteration += 1

        debugPrint(f"Heuristic calculated: {totalCost}")
        return totalCost

    def validateTotalContainers(self, initialCount):
        bayCount = sum(len(stack) for stack in self.bay.values())
        bufferCount = sum(len(stack) for stack in self.buffer.values())
        totalCount = bayCount + bufferCount + len(self.currentOff) + len(self.load)
        if totalCount != initialCount:
            debugPrint("ERROR: Container count mismatch!")
            debugPrint(f"Expected: {initialCount}, Found: {totalCount}")
            debugPrint(f"Bay count: {bayCount}, Buffer count: {bufferCount}, Current Off count: {len(self.currentOff)}, Load count: {len(self.load)}")
            self.printState()
            debugPrint("Full Bay State:")
            for col, stack in self.bay.items():
                debugPrint(f"  Column {col}: {[container.name for container in stack]}")
            debugPrint("Full Buffer State:")
            for col, stack in self.buffer.items():
                debugPrint(f"  Column {col}: {[container.name for container in stack]}")
            debugPrint("Full Current Off State:")
            debugPrint([container.name for container in self.currentOff])
            debugPrint("Full Load State:")
            debugPrint([container.name for container in self.load])
            raise ValueError("Container count mismatch")



    def __lt__(self, other):
        return self.f < other.f

    def __eq__(self, other):
        return (
            sorted(self.bay.items()) == sorted(other.bay.items()) and
            sorted(self.buffer.items()) == sorted(other.buffer.items()) and
            Counter(self.currentOff) == Counter(other.currentOff) and
            Counter(self.load) == Counter(other.load)
        )


    def __hash__(self):
        bayHash = frozenset((k, tuple(v)) for k, v in sorted(self.bay.items()))
        bufferHash = frozenset((k, tuple(v)) for k, v in sorted(self.buffer.items()))
        currentOffHash = frozenset(container.name for container in self.currentOff)
        loadHash = frozenset(container.name for container in self.load)
        return hash((bayHash, bufferHash, currentOffHash, loadHash))



    def printState(self):
        print("Current state of the bay, buffer, current offload, and load:")
        nameWidth = 14
        weightWidth = 5

        print("Bay State:")
        for row in range(testX - 1, -1, -1):
            for column in range(testY):
                if column in self.bay and row < len(self.bay[column]):
                    container = self.bay[column][row]
                    name = f"{container.name}".ljust(nameWidth)
                    weight = f"{container.weight}".ljust(weightWidth)
                    print(f"| {name} {weight} |", end='')
                else:
                    emptyName = "UNUSED".ljust(nameWidth)
                    emptyWeight = "0".ljust(weightWidth)
                    print(f"| {emptyName} {emptyWeight} |", end='')
            print()

        print("\nBuffer State:")
        for row in range(testBufferX - 1, -1, -1):
            for bufferCol in range(testBufferY):
                if bufferCol in self.buffer and row < len(self.buffer[bufferCol]):
                    container = self.buffer[bufferCol][row]
                    name = f"{container.name}".ljust(nameWidth)
                    weight = f"{container.weight}".ljust(weightWidth)
                    print(f"| {name} {weight} |", end='')
                else:
                    emptyName = "UNUSED".ljust(nameWidth)
                    emptyWeight = "0".ljust(weightWidth)
                    print(f"| {emptyName} {emptyWeight} |", end='')
            print()

        print("\nNeeded Off:")
        for container in self.neededOff:
            print(f"  - Name: {container.name}, Weight: {container.weight}")

        print("\nCurrent Off:")
        for container in self.currentOff:
            print(f"  - Name: {container.name}, Weight: {container.weight}")

        print("\nLoad State:")
        for container in self.load:
            print(f"  - Name: {container.name}, Weight: {container.weight}")
        print()



class Tree:
    def __init__(self, filePath, neededOff, load, igrid):
        currentOff = []
        debugPrint("Tree initialized with root BoardState.")
        grid = igrid
        buffer = defaultdict(list)
        for i in range(testBufferX):
            buffer[i] = []
        self.root = BoardState(grid, buffer, neededOff, currentOff, load, 0, None)
        self.initialCount = (
            sum(len(stack) for stack in self.root.bay.values()) +
            sum(len(stack) for stack in self.root.buffer.values()) +
            len(self.root.currentOff) +
            len(self.root.load)
        )


        self.statesExpanded = 0
        self.maxDepthReached = 0
        self.totalNodesGenerated = 0

    def traceSolution(self, goalState):
        moves = []
        current = goalState
        while current.parent:
            moves.append((current.moveDescription, current.movePositions))
            current = current.parent
        moves.reverse()
        print("\nSolution Moves:")
        for i, (desc, positions) in enumerate(moves, 1):
            print(f"{i}. {desc}")
            print(f"   Positions: Initial {positions[0]} -> Final {positions[1]}")
        return moves

    def aStar(self):
        debugPrint("Starting A* search...")
        frontier = []
        heapq.heappush(frontier, (self.root.f, self.root))
        frontierSet = {self.root}
        visitedSet = set()

        while frontier:
            debugPrint(f"Frontier size: {len(frontier)}, Visited size: {len(visitedSet)}")
            _, curr = heapq.heappop(frontier)
            frontierSet.remove(curr)

            self.statesExpanded += 1
            self.maxDepthReached = max(self.maxDepthReached, curr.depth)

            debugPrint(f"Exploring state with f={curr.f} (g={curr.g}, h={curr.h})")
            if DEBUG:
                curr.printState()

            # input("Press Enter to continue to the next iteration...")

            if self.isGoal(curr):
                curr.printState()
                print("\nSearch Statistics:")
                print(f"  Total States Expanded: {self.statesExpanded}")
                print(f"  Maximum Depth Reached: {self.maxDepthReached}")
                print(f"  Total Nodes Generated: {self.totalNodesGenerated}")
                return self.traceSolution(curr)
            
            visitedSet.add(curr)
            debugPrint("Expanding current state...")
            self.expand(curr, frontier, frontierSet, visitedSet)

    def expand(self, curr, frontier, frontierSet, visitedSet):
        debugPrint(f"Expanding children of node at depth {curr.depth}...")

        for column in range(testX):
            if column in curr.bay and curr.bay[column]:
                debugPrint(f"  Exploring bay column {column} with {len(curr.bay[column])} containers...")

                top = curr.bay[column][-1]
                position = (column + 1, len(curr.bay[column]))
                debugPrint(f"    Accessed container '{top.name}' from position {position}")

                if top.name == "NAN" and top.weight == 0:
                    debugPrint(f"    Skipping container '{top.name}' with weight '{top.weight}' as it is not movable.")
                    continue

                for otherColumn in range(testX):
                    if otherColumn == column:
                        continue

                    if len(curr.bay[otherColumn]) >= testY:
                        debugPrint(f"    Cannot move to bay column {otherColumn}: height limit exceeded.")
                        continue

                    debugPrint(f"    Trying to move container to bay column {otherColumn}...")
                    newBay = copy.deepcopy(curr.bay)
                    newBay[column] = newBay[column][:-1]
                    newBay[otherColumn].append(top)

                    newCost = abs(position[0] - (otherColumn + 1)) + abs(position[1] - len(newBay[otherColumn]))
                    moveDescription = f"Move '{top.name}' from bay column {column + 1} to bay column {otherColumn + 1}"
                    movePositions = [(column + 1, position[1]), (otherColumn + 1, len(newBay[otherColumn]))]

                    child = BoardState(
                        newBay, copy.deepcopy(curr.buffer), curr.neededOff, copy.deepcopy(curr.currentOff),
                        curr.load, curr.g + newCost, curr, moveDescription, movePositions
                    )
                    child.validateTotalContainers(self.initialCount)

                    debugPrint(f"      Generated child node at depth {child.depth}")
                    self.totalNodesGenerated += 1

                    if child not in visitedSet and child not in frontierSet:
                        debugPrint(f"      Adding child node at depth {child.depth} to frontier.")
                        heapq.heappush(frontier, (child.f, child))
                        frontierSet.add(child)

                for bufferCol in range(testBufferX):
                    if len(curr.buffer[bufferCol]) >= testBufferY:
                        debugPrint(f"    Cannot move to buffer column {bufferCol}: height limit exceeded.")
                        continue

                    debugPrint(f"    Trying to move container to buffer column {bufferCol}...")
                    newBay = copy.deepcopy(curr.bay)
                    newBay[column] = newBay[column][:-1]
                    newBuffer = copy.deepcopy(curr.buffer)
                    newBuffer[bufferCol].append(top)

                    newCost = abs(position[0]) + abs(position[1] - (testY + 1)) + 4 + abs(testBufferX - bufferCol + 1) + abs((testBufferY + 1) - len(newBuffer[bufferCol]))
                    moveDescription = f"Move '{top.name}' from bay column {column + 1} to buffer column {bufferCol + 1}"
                    movePositions = [(column + 1, position[1]), f"Buffer {bufferCol + 1}"]

                    child = BoardState(
                        newBay, newBuffer, curr.neededOff, copy.deepcopy(curr.currentOff),
                        curr.load, curr.g + newCost, curr, moveDescription, movePositions
                    )
                    child.validateTotalContainers(self.initialCount)

                    debugPrint(f"      Generated child node at depth {child.depth}")
                    self.totalNodesGenerated += 1

                    if child not in visitedSet and child not in frontierSet:
                        debugPrint(f"      Adding child node at depth {child.depth} to frontier.")
                        heapq.heappush(frontier, (child.f, child))
                        frontierSet.add(child)

                if top in curr.neededOff:
                    debugPrint(f"    Trying to move container '{top.name}' to offload...")
                    newBay = copy.deepcopy(curr.bay)
                    newBay[column] = newBay[column][:-1]
                    newCurrOff = copy.deepcopy(curr.currentOff)
                    newCurrOff.append(top)

                    newCost = abs(position[0]) + abs(position[1] - (testY + 1)) + 2
                    moveDescription = f"Move '{top.name}' from column {column + 1} to OFFLOAD"
                    movePositions = [(column + 1, position[1]), "OFFLOAD"]

                    child = BoardState(
                        newBay, copy.deepcopy(curr.buffer), curr.neededOff, newCurrOff,
                        curr.load, curr.g + newCost, curr, moveDescription, movePositions
                    )
                    child.validateTotalContainers(self.initialCount)

                    debugPrint(f"      Generated child node at depth {child.depth}")
                    self.totalNodesGenerated += 1

                    if child not in visitedSet and child not in frontierSet:
                        debugPrint(f"      Adding child node at depth {child.depth} to frontier.")
                        heapq.heappush(frontier, (child.f, child))
                        frontierSet.add(child)

        for loadContainer in curr.load:
            debugPrint(f"  Trying to load container '{loadContainer.name}' into the bay...")

            for column in range(testX):
                if len(curr.bay[column]) >= testY:
                    debugPrint(f"    Cannot load into bay column {column}: height limit exceeded.")
                    continue

                newBay = copy.deepcopy(curr.bay)
                newLoad = [container for container in curr.load if container != loadContainer]
                newBay[column].append(loadContainer)

                newCost = 2 + abs(column) + abs((testY + 1) - len(newBay[column]))
                moveDescription = f"Load '{loadContainer.name}' into bay column {column + 1}"
                movePositions = ["Load", (column + 1, len(newBay[column]))]

                child = BoardState(
                    newBay, copy.deepcopy(curr.buffer), curr.neededOff, copy.deepcopy(curr.currentOff),
                    newLoad, curr.g + newCost, curr, moveDescription, movePositions
                )
                child.validateTotalContainers(self.initialCount)

                debugPrint(f"      Generated child node at depth {child.depth}")
                self.totalNodesGenerated += 1

                if child not in visitedSet and child not in frontierSet:
                    debugPrint(f"      Adding child node at depth {child.depth} to frontier.")
                    heapq.heappush(frontier, (child.f, child))
                    frontierSet.add(child)


    def isGoal(self, curr):
        debugPrint("Checking goal state...")

        if Counter(curr.neededOff) != Counter(curr.currentOff):
            debugPrint("Not all needed containers are offloaded.")
            return False

        if any(curr.buffer[col] for col in curr.buffer):
            debugPrint("Buffer is not empty.")
            return False

        if curr.load:
            debugPrint("Load is not empty.")
            return False

        debugPrint("Goal state confirmed.")
        return True

def main():
    startTime = time.time()
    filePath = 'C:\\Users\\edech\\Documents\\BEAM-Solutions-Project\\load\\test_manifest.txt'
    neededOff = [manifest_read.A_Container(0, '6LBdogs500'), manifest_read.A_Container(0, 'Maersk')]
    load = [manifest_read.A_Container(0, 'Sunshine'), manifest_read.A_Container(0, 'Rainbows')]
    tree = Tree(filePath, neededOff, load)
    moves = tree.aStar()

    endTime = time.time()

    runtimeSeconds = endTime - startTime
    runtimeMinutes = runtimeSeconds / 60

    print(f"Runtime: {runtimeSeconds:.2f} seconds ({runtimeMinutes:.2f} minutes)")
    print("\nMoves as a list:")
    print(moves)

if __name__ == "__main__":
    main()
