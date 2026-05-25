def printTable(table):
    colWidths=[0]*len(table)
for i in range(len(table)):
    for item in table[i]:
        if len(item)>colWidths[i]:
            colWidths[i]=len(item)
    for row in range(len(table[0])):
        for col in range(len(table)):
            print(table[col][row].rjust(colWidths[col],end=''))
        print()
tableData=[
    ['apples','oranges','cherries','banana'],
    ['Alice','BOb','Carol','David'],
    ['dogs','cats','moose','goose']
]
printTable(tableData)
                
