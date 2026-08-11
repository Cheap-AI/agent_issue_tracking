#badges

badge_records = [
    ["Paul", "1350", "enter"],
    ["Paul", "1355", "exit"],
    ["Abby", "1400", "enter"],
    ["Reg", "1410", "enter"],
    ["Abby", "1415", "exit"],
    ["Reg", "1420", "enter"], # Reg enters twice without exiting
    ["Chris", "1430", "exit"], # Chris exits without entering
]
#All employees who exited without a corresponding entry record active at that time.
#All employees who entered but never exited by the end of the log
#I am gonna use dict
def sol(badge_records):
    inside_room = set()
    exit_without_entry = set()
    enter_then_no_exit = set()
    for name, time, action in badge_records:
        if action == "enter":
            if name in inside_room:
                enter_then_no_exit.add(name)
            elif name not in inside_room:
                inside_room.add(name)
    
        elif action == "exit":
            if name in inside_room:
                inside_room.discard(name)

            elif name not in inside_room:
                exit_without_entry.add(name)
    
    return enter_then_no_exit, exit_without_entry


###     
from collections import defaultdict

def find_nodes_by_parents(pairs):
    all_individuals = set()
    parent_counts = defaultdict(int)
    
    # Step 1: Populate counts and individuals
    for parent, child in pairs:
        all_individuals.add(parent)
        all_individuals.add(child)
        
        # Increment parent count for this child
        parent_counts[child] += 1
        
    zero_parents = set()
    one_parent = set()
    
    # Step 2: Categorize every unique individual we found
    for person in all_individuals:
        if person not in parent_counts:
            # If they are not in parent_counts, 0 arrows point to them!
            zero_parents.add(person)
        elif parent_counts[person] == 1:
            # Exactly 1 arrow points to them
            one_parent.add(person)
            
    return zero_parents, one_parent

aaaaabbbbcccc / a5....

def comp_str(s: str) -> str:

    if not s:
        return ""
    
    compressed = []
    #char_point = s[0]
    count = 1

    for i in range(1, len(s)):
        if s[i] == s[i-1]:
            count += 1
        else:
            compressed.append(f"{char_point}{count}")
            char_point=str[i]
            count = 1

    compressed.append(f"{char_point}{count}")

    return "".join(compressed)
from typing import List

def three_sum(nums: List[int]) -> List[List[int]]:
    nums.sort()


    solution = []


    for i in range(len(nums)-2):

        if i>0 and nums[i] == nums[i-1]:
            continue
            
        if nums[i] >0:
            break

        j = i+1
        k = len(nums)-1
        


        while j < k:
        
            current_sum =nums[i] + nums[j] + nums[k]
            if current_sum < 0:
                j += 1
            elif current_sum > 0:
                k -= 1
            elif current_sum == 0:
                solution.append([nums[i],nums[j],nums[k]])
                while j < k and nums[j] == nums[j + 1]:
                    j += 1
                while j < k and nums[k] == nums[k - 1]:
                    k -= 1        
                j+=1
                k-=1
    return solution

def check_board(board):
    for row in board:
        seen = set()

        for value in row:
            if value == ".":
                continue
            elif value in seen:
                return False
            else:
                seen.add(value)
    
    for col in range(9):
        seen = set()
        
        for row in range(9):

            if board[row][col] == ".":
                continue
            

            elif board[row][col] in seen:
                return False
            else:
                seen.add(board[row][col])

    for start_row in range(0,9,3):
        for start_col in range(0,9,3):
            seen = set()

            for i in range(start_row, start_row+3):
                for j in range(start_col,start_row+3):
                    value = board[i][j]
                    if value == ".":
                        continue
                    elif value in seen:
                        return False
                    elif value not in seen:
                        seen.add(value)
    
    return True

def is_valid_group(values):

    seen = set()

    for value in values:

        if value == ".":
            continue

        if value in seen:
            return False

        seen.add(value)

    return True

def find_valid_subgrids(matrix, k):
    result_sets = []

    for r in range(len(matrix)-k+1):
        for c in range(len(matrix[0])-k+1):
            values = []
            for i in range(r, r+k):
                for j in range(c, c+k):
                    values.append(matrix[i][j])
            if is_valid_group(values):
                result_sets.append([r,c])

    return result_sets


from collections import defaultdict

def find_badges(logs):
    ordered_entry = defaultdict(list)

    for name, time in logs:
        ordered_entry[name].append(time)

    for name in ordered_entry:
        ordered_entry[name].sort()

    