# -*- coding: utf-8 -*-
import binascii
import sys
import json
import math
import struct
import functools
from collections import OrderedDict


hexFile = b''
rebuildFileTemp = bytearray()
exportDict = OrderedDict()
stringOffsetTable = []
stringTable = []
stringOffsetTable2 = []
stringTable2 = []
textOffsetTable = []
textTable = []
columnContentOffsetTable = []
ValidityBoolTable = []




def readFromPosition (offset, size, value_type):
    valueToRead=(binascii.unhexlify(hexFile[offset*2:(offset+size)*2]))
    valueToRead=struct.unpack(value_type,valueToRead)
    valueToRead=functools.reduce(lambda rst, d: rst * 10 + d, (valueToRead))
    if type(valueToRead) is bytes: #String gets unpacked as bytes, we want to convert it to a regular string
        valueToRead = valueToRead.decode()
    return valueToRead



def writeToPosition (target, offset, size, value):
    target[offset:offset + size] = value
    return target



def swapEndian(hexStr, value_type):
    original_value = binascii.unhexlify(hexStr)
    value = struct.unpack(value_type, original_value)
    value = functools.reduce(lambda rst, d: rst * 10 + d, (value))
    return value



def calculateSeparator(end): #Calculates the amount of null bytes that need to be added
    last_part_offset = int(hex(int(end))[-1],16) #This is retarded

	#Check the last digit of the hex value to calculate the amount that needs to be filled for the next table to start
    if (last_part_offset<0x4): 
        return 0x4-last_part_offset
    elif (last_part_offset>=0x4 and last_part_offset<0x8):
        return 0x8-last_part_offset
    elif (last_part_offset>=0x8 and last_part_offset<0xC):
        return 0xC-last_part_offset
    elif (last_part_offset>=0xC and last_part_offset<0x10):
        return 0x10-last_part_offset
    else:
        return 1



def storeTable (startOffset, tableSize, tableContainer): #Stores every entry of the table into the selected variable
    byteGroup = ""
    table = hexFile[(startOffset*2) : (startOffset*2)+(tableSize*4)*2].decode('utf-8')

    for nibble in table:
        if (len(byteGroup) <8):
            byteGroup += nibble

        if (len(byteGroup) == 8):
            tableContainer.append(byteGroup)
            byteGroup= ""



def iteratePlainTextTable (tableContainer, offsetTable):
    for offset in offsetTable:
        offset = swapEndian(offset, "<I")
        table = hexFile[(offset*2):] #A bit of a dirty approach but it will do for now
        string_end = table.find(b'00') 
        if (string_end % 2 != 0): #If the last hex digit ends with 0, the pointer will be odd, so we compensate adding 1
            string_end += 1
        string = binascii.unhexlify (table[:string_end]).decode()
        tableContainer.append(string)



def getColumnValueTextTableIndex (pointerToTable, numberOfEntries, row_index):
    table = hexFile[(pointerToTable*2):(pointerToTable + numberOfEntries*4)*2]
    table = [table[i:i+(4*2)] for i in range(0, len(table), (4*2))]
    index = table[row_index]    
    if (index == b'ffffffff'):
        return -1
    else:
        index = swapEndian(index, "<I")
        return index
        



def iterateValueTable (pointerToTable, numberOfEntries, valueType, valueSize):
    table = hexFile[(pointerToTable*2):(pointerToTable + numberOfEntries*valueSize)*2]
    table = [table[i:i+(valueSize*2)] for i in range(0, len(table), (valueSize*2))]
    returnList = []
    for entry in table:
        value = binascii.unhexlify(entry)
        value = struct.unpack(valueType , value)
        value = functools.reduce(lambda rst, d: rst * 10 + d, (value))
        returnList.append(value)
    return returnList



def iterateValidityBoolTable (pointerToTable, numberOfEntries):
    table = hexFile[(pointerToTable*2):(pointerToTable + numberOfEntries*4)*2]
    table = [table[i:i+2] for i in range(0, len(table), 2)]
    returnList = []
    for entry in table:
        entry_binary = "{0:08b}".format(int(entry,16))
        returnList.append(entry_binary)
    return returnList



def iterateBitmaskTable (pointerToTable, numberOfEntries):
    table = hexFile[(pointerToTable*2):(pointerToTable + abs(math.ceil(numberOfEntries/8)))*2]
    table = [table[i:i+2] for i in range(0, len(table), 2)]
    returnList = []
    for entry in table:
        entry_binary = list("{0:08b}".format(int(entry,16)))
        entry_binary.reverse()
        returnList.extend(entry_binary)
    return returnList



def getColumnInfo (pointerToBytesArray1, pointerToBytesArray2, pointerToBitsArray2, columnCount):
    columnInfo = OrderedDict()
    columnValidity = OrderedDict()
    columnTypes = OrderedDict()
    columnTypes2 = OrderedDict()
    types = iterateValueTable (pointerToBytesArray2, columnCount, "<b", 1)
    types2 = iterateValueTable (pointerToBytesArray1, columnCount, "<b", 1)
    validity = iterateBitmaskTable (pointerToBitsArray2, columnCount)
    iterator = 0

    for column in stringTable2:
        columnValidity[column] = validity[iterator]
        columnTypes[column] = types[iterator]
        columnTypes2[column] = types2[iterator]
        iterator += 1

    columnInfo["columnValidity"] = columnValidity
    columnInfo["columnTypes"] = columnTypes
    columnInfo["columnTypes2"] = columnTypes2
    return columnInfo



def exportFile ():
    with open(file_path, "rb") as f:
        file=f.read()
    global hexFile
    hexFile=(binascii.hexlify(file))

    fileSize =                      len(hexFile)
    pointerToMainTable =            readFromPosition (0x10, 0x4, "<i")
    rowCount =                      readFromPosition (pointerToMainTable + 0x0, 0x4, "<i")
    columnCount =                   readFromPosition (pointerToMainTable + 0x4, 0x4, "<i")
    textCount =                     readFromPosition (pointerToMainTable + 0x8, 0x4, "<i")
    pointerToStringOffsetTable =    readFromPosition (pointerToMainTable + 0x10, 0x4, "<i")
    pointerToBitArray1 =            readFromPosition (pointerToMainTable + 0x14, 0x4, "<i")
    pointerToBytesArray1 =          readFromPosition (pointerToMainTable + 0x18, 0x4, "<i")
    pointerToIntArray1 =            readFromPosition (pointerToMainTable + 0x1C, 0x4, "<i")
    pointerToTextOffsetTable =      readFromPosition (pointerToMainTable + 0x24, 0x4, "<i")
    pointerToStringOffsetTable2 =   readFromPosition (pointerToMainTable + 0x28, 0x4, "<i")
    pointerToIntArray2 =            readFromPosition (pointerToMainTable + 0x30, 0x4, "<i")
    pointerToIntArray3 =            readFromPosition (pointerToMainTable + 0x34, 0x4, "<i")
    pointerToBitsArray2 =           readFromPosition (pointerToMainTable + 0x38, 0x4, "<i")
    pointerToAnotherTable =         readFromPosition (pointerToMainTable + 0x3C, 0x4, "<i")
    pointerToBytesArray2 =          readFromPosition (pointerToMainTable + 0x48, 0x4, "<i")
    pointerToBytesArray3 =          readFromPosition (pointerToMainTable + 0x4C, 0x4, "<i")


    #DEBUG OUTPUT
    print ("File size: " + str(fileSize))
    print ("Pointer to Main Table: " + str(pointerToMainTable))
    print ("Row Count: " + str(rowCount))
    print ("Column Count: " + str(columnCount))
    print ("Text Count: " + str(textCount))
    print ("Pointer to String Offset Table: " + str(pointerToStringOffsetTable))
    print ("Pointer to Bits Array Table: " + str(pointerToBitArray1))
    print ("Pointer to Byte Array Table: " + str(pointerToBytesArray1))
    print ("Pointer to Int Array Table: " + str(pointerToIntArray1))
    print ("Pointer to Text Offset Table: " + str(pointerToTextOffsetTable))
    print ("Pointer to String Offset Table 2: " + str(pointerToStringOffsetTable2))
    print ("Pointer to Int Array Table 2: " + str(pointerToIntArray2))
    print ("Pointer to Int Array Table 3: " + str(pointerToIntArray3))
    print ("Pointer to Bit Array Table 2: " + str(pointerToBitsArray2))
    print ("Pointer to Another Table: " + str(pointerToAnotherTable))
    print ("Pointer to Column Type Table: " + str(pointerToBytesArray2))
    print ("Pointer to Byte Array Table 3: " + str(pointerToBytesArray3))

    print ("\nExporting...")


    storeTable (pointerToStringOffsetTable, rowCount, stringOffsetTable) #Strings 1 / Rows
    iteratePlainTextTable (stringTable, stringOffsetTable)
    storeTable (pointerToStringOffsetTable2, columnCount, stringOffsetTable2) #Strings 2 / Columns
    iteratePlainTextTable (stringTable2, stringOffsetTable2)


    #Columns
    if (columnCount > 0):
        global columnContentOffsetTable
        storeTable (pointerToIntArray1, columnCount, columnContentOffsetTable) 
        offsetTable = []
        for offset in columnContentOffsetTable:
            offsetTable.append(swapEndian(offset, "<I"))
        columnContentOffsetTable = offsetTable
        

    #Text
    if (textCount > 0):
        storeTable (pointerToTextOffsetTable, textCount, textOffsetTable) 
        iteratePlainTextTable (textTable, textOffsetTable)


    #ValidityBool
    if (pointerToBytesArray3 != 0 and pointerToBytesArray3 != fileSize): 
        validityBoolTable = iterateValidityBoolTable(pointerToBytesArray3, rowCount) 
    else:
        validityBoolTable = None


    #Row validity
    row_validity = iterateBitmaskTable (pointerToBitArray1, rowCount)
        





    # PREPARE THE EXPORT DICTIONARY AND SAVE AS JSON
    exportDict["ROW_COUNT"] = rowCount
    exportDict["COLUMN_COUNT"] = columnCount
    exportDict["TEXT_COUNT"] = textCount

    exportDict.update ( getColumnInfo(pointerToBytesArray1, pointerToBytesArray2, pointerToBitsArray2, columnCount) )


    #Store Column values
    columnValues = {}
    for column in stringTable2:
        column_index = stringTable2.index(column)

        if (exportDict["columnTypes"][str(column)] == -1): #Skip unused columns
            emptyList = []
            columnValues[column] = emptyList
            continue

        if (exportDict["columnTypes"][str(column)] == 0): #Int8 unsigned
            valueTable = iterateValueTable (columnContentOffsetTable[column_index], rowCount, "<B", 1)
            columnValues[column] = valueTable
            continue

        if (exportDict["columnTypes"][str(column)] == 1): #Int16 unsigned
            valueTable = iterateValueTable (columnContentOffsetTable[column_index], rowCount, "<H", 2)
            columnValues[column] = valueTable
            continue

        if (exportDict["columnTypes"][str(column)] == 2): #Int32 unsigned
            valueTable = iterateValueTable (columnContentOffsetTable[column_index], rowCount, "<I", 4)
            columnValues[column] = valueTable
            continue

        if (exportDict["columnTypes"][str(column)] == 3): #Int64 unsigned
            valueTable = iterateValueTable (columnContentOffsetTable[column_index], rowCount, "<Q", 8)
            columnValues[column] = valueTable
            continue

        if (exportDict["columnTypes"][str(column)] == 4): #Int8 signed
            valueTable = iterateValueTable (columnContentOffsetTable[column_index], rowCount, "<b", 1)
            columnValues[column] = valueTable
            continue

        if (exportDict["columnTypes"][str(column)] == 5): #Int16 signed
            valueTable = iterateValueTable (columnContentOffsetTable[column_index], rowCount, "<h", 2)
            columnValues[column] = valueTable
            continue

        if (exportDict["columnTypes"][str(column)] == 6): #Int32 unsigned
            valueTable = iterateValueTable (columnContentOffsetTable[column_index], rowCount, "<i", 4)
            columnValues[column] = valueTable
            continue

        if (exportDict["columnTypes"][str(column)] == 7): #Int64 unsigned
            valueTable = iterateValueTable (columnContentOffsetTable[column_index], rowCount, "<q", 8)
            columnValues[column] = valueTable
            continue

        if (exportDict["columnTypes"][str(column)] == 9): #float32 unsigned
            valueTable = iterateValueTable (columnContentOffsetTable[column_index], rowCount, "<f", 4)
            columnValues[column] = valueTable
            continue

        if (exportDict["columnTypes"][str(column)] == 11): #boolean unsigned
            valueTable = iterateBitmaskTable (columnContentOffsetTable[column_index], rowCount)
            columnValues[column] = valueTable
            continue



    row_index = 0
    for row in stringTable: #Element per row
        columnDict = OrderedDict() #Column contents will be stored here
        columnDict[row] = {}


        for column in stringTable2: #Iterate through each column
            column_index = stringTable2.index(column)

            if (exportDict["columnTypes"][str(column)] == -1): #Skip unused columns
                continue

            if (exportDict["columnTypes"][str(column)] in range(0, 12)):
                columnData = {str(column) : columnValues[column][row_index]}
                columnDict[row].update(columnData)
                continue

            if (exportDict["columnTypes"][str(column)] == 12): #String
                index = getColumnValueTextTableIndex (columnContentOffsetTable[column_index], rowCount, row_index)
                if (index == -1):
                    continue
                columnData = {str(column) : textTable[index]}
                columnDict[row].update(columnData)
                continue


        #Add the validityBool if present
        if (validityBoolTable is not None): 
            columnData = {"validityBool" : validityBoolTable[row_index]}
            columnDict[row].update(columnData)


        columnData = {"isValid" : row_validity[row_index]}
        columnDict[row].update(columnData)

        
        exportDict[row_index] = columnDict
        print ("Entry "+str(row_index) + " / "+str(rowCount))
        row_index +=1


    with open(file_name +'.json', 'w', encoding='utf8') as file:
        json.dump(exportDict, file, indent=2, ensure_ascii=False)


















def storeJSONInfo (data):
    #print(data)
    row_count = data['ROW_COUNT']
    column_count = data['COLUMN_COUNT']
    text_count = data['TEXT_COUNT']

    rowNames = []
    for entry in range(0, row_count): #Store row names
        rowNames.append( list(data[str(entry)])[0] )

    columnNames = list(data['columnValidity'].keys()) #Store column names

    rowContent = []
    for entry in range(0, row_count):
        rowContent.append( data[str(entry)][rowNames[entry]] )


    text = []
    if text_count > 0: #Store Text
        for entry in range(0, row_count):
            for column in columnNames:
                if data['columnTypes'][column] == 12:
                    if column in data[str(entry)][rowNames[entry]]:
                        string = data[str(entry)][rowNames[entry]][str(column)]
                        if string not in text:
                            text.append(string)


    if 'validityBool' in rowContent[0]:
        has_validitybool = True
    else:
        has_validitybool = False
    
    jsonInfo = {'ROW_COUNT' : row_count, 'COLUMN_COUNT' : column_count, 'TEXT_COUNT' : text_count, 'ROW_NAMES' : rowNames, 'COLUMN_NAMES' : columnNames, 'TEXT' : text, 'ROW_CONTENT' : rowContent, 'HAS_VALIDITYBOOL' : has_validitybool}
    return jsonInfo


    
def rebuildFile ():
    with open(file_path, 'r', encoding='utf8') as file:
        data = json.load(file)
        jsonInfo = storeJSONInfo(data)
        print ("Rebuilding...")
        global rebuildFileTemp

        rebuildFileTemp += b'\x61\x72\x6D\x70' #Add magic
        rebuildFileTemp += b'\x00\x00\x00\x00'
        rebuildFileTemp += b'\x0C\x00\x01\x00' #Version used by FOTNS, 6 and K2
        rebuildFileTemp += b'\x00\x00\x00\x00'
        rebuildFileTemp += b'\x20\x00\x00\x00' #Pointer to main table (will always be the same on single-table files)
        rebuildFileTemp += b'\x00\x00\x00\x00'*3 #Fill padding
        rebuildFileTemp += b'\x00\x00\x00\x00'*20 #Set the main table to all zeros for now


        #Row Validity
        pointerToBitArray1 = len(rebuildFileTemp)
        #rebuildFileTemp += b'\xFF' * int(math.ceil(jsonInfo["ROW_COUNT"]/8) ) # Write a dummy bitarray1 with all the flags set to 1
        binary = ''
        for row in range(0, jsonInfo['ROW_COUNT']):
            bit = jsonInfo['ROW_CONTENT'][row]['isValid']
            if len(binary) < 8:
                binary += bit
            if len(binary) == 8:
                binary = binary[::-1]
                binary = int(binary, 2).to_bytes(1, 'little')
                rebuildFileTemp += binary
                binary = ''
            if row == jsonInfo['ROW_COUNT']-1:
                binary = binary.ljust(8, '0')
                binary = binary[::-1]
                binary = int(binary, 2).to_bytes(1, 'little')
                rebuildFileTemp += binary

        rebuildFileTemp = writeToPosition(rebuildFileTemp, 0x34, 0x4, int(pointerToBitArray1).to_bytes(4, 'little') )
        rebuildFileTemp += b'\x00\x00\x00\x00' + b'\x00'*calculateSeparator(len(rebuildFileTemp)) #Padding


        #Column Validity
        pointerToBitArray2 = len(rebuildFileTemp)
        #rebuildFileTemp += b'FF' * int(math.ceil(jsonInfo["COLUMN_COUNT"]/8) ) # Write a dummy bitarray2 with all the flags set to 1
        binary = ''
        for column in range(0, jsonInfo['COLUMN_COUNT']):
            bit = data['columnValidity'][jsonInfo['COLUMN_NAMES'][column]]
            if len(binary) < 8:
                binary += bit
            if len(binary) == 8:
                binary = binary[::-1]
                binary = int(binary, 2).to_bytes(1, 'little')
                rebuildFileTemp += binary
                binary = ''
            if column == jsonInfo['COLUMN_COUNT']-1:
                binary = binary.ljust(8, '0')
                binary = binary[::-1]
                binary = int(binary, 2).to_bytes(1, 'little')
                rebuildFileTemp += binary
        
        rebuildFileTemp = writeToPosition(rebuildFileTemp, 0x58, 0x4, int(pointerToBitArray2).to_bytes(4, 'little') )
        rebuildFileTemp += b'\x00'*calculateSeparator(len(rebuildFileTemp)) #Padding


        #Row Entries
        stringOffsetTableTemp = []
        for x in range(jsonInfo["ROW_COUNT"]): #Write row String table and store offsets for the String offset table
            stringOffsetTableTemp.append(len(rebuildFileTemp))
            rebuildFileTemp += jsonInfo["ROW_NAMES"][x].encode()
            rebuildFileTemp += b'\x00' #Null byte
        rebuildFileTemp += b'\x00' * calculateSeparator(len(rebuildFileTemp)) #Add null bytes at the end of the String table

        #Row Entries Offset Table
        stringOffsetTableOffset = len(rebuildFileTemp)
        for x in range(jsonInfo["ROW_COUNT"]): #Write String Offset table
            rebuildFileTemp += int(stringOffsetTableTemp[x]).to_bytes(4, 'little')    

        #Row Entries and Row Entries Offset table pointers in Main Table
        rebuildFileTemp = writeToPosition(rebuildFileTemp, 0x20, 0x4, jsonInfo["ROW_COUNT"].to_bytes(4, 'little') ) #Add the number of rows to the main table
        rebuildFileTemp = writeToPosition(rebuildFileTemp, 0x30, 0x4, int(stringOffsetTableOffset).to_bytes(4, 'little') ) #Add the pointer to the String Offset table to the main table

        
        #Column Names
        if jsonInfo['COLUMN_COUNT'] > 0:
            stringOffsetTable2Temp = []
            for x in range(jsonInfo["COLUMN_COUNT"]): #Write Column String table and store offsets for the String offset table 2
                stringOffsetTable2Temp.append(len(rebuildFileTemp))
                rebuildFileTemp += jsonInfo["COLUMN_NAMES"][x].encode()
                rebuildFileTemp += b'\x00' #Null byte
            rebuildFileTemp += b'\x00' * calculateSeparator(len(rebuildFileTemp)) #Add null bytes at the end of the String table 2

            #Column Names Offset Table
            stringOffsetTable2Offset = len(rebuildFileTemp)
            for x in range(jsonInfo["COLUMN_COUNT"]): #Write String Offset table 2
                rebuildFileTemp += int(stringOffsetTable2Temp[x]).to_bytes(4, 'little') 

            #Column Names and Column Names Offset table pointers in Main Table
            rebuildFileTemp = writeToPosition(rebuildFileTemp, 0x24, 0x4, jsonInfo["COLUMN_COUNT"].to_bytes(4, 'little') ) #Add the number of rows to the main table
            rebuildFileTemp = writeToPosition(rebuildFileTemp, 0x48, 0x4, int(stringOffsetTable2Offset).to_bytes(4, 'little') ) #Add the pointer to the String Offset table 2 to the main table


        #Text
        if jsonInfo['TEXT_COUNT'] > 0:
            textOffsetTableTemp = []
            for text in jsonInfo["TEXT"]: #Write Column String table and store offsets for the String offset table 2
                textOffsetTableTemp.append(len(rebuildFileTemp))
                rebuildFileTemp += text.encode()
                rebuildFileTemp += b'\x00' #Null byte
            rebuildFileTemp += b'\x00' * calculateSeparator(len(rebuildFileTemp)) #Add null bytes at the end of the String table 2

            #Text Offset Table
            textOffsetTableOffset = len(rebuildFileTemp)
            for x in range(jsonInfo["TEXT_COUNT"]): #Write String Offset table 2
                rebuildFileTemp += int(textOffsetTableTemp[x]).to_bytes(4, 'little') 

            #Text and Text Offset table pointers in Main Table
            rebuildFileTemp = writeToPosition(rebuildFileTemp, 0x28, 0x4, jsonInfo["TEXT_COUNT"].to_bytes(4, 'little') ) #Add the number of rows to the main table
            rebuildFileTemp = writeToPosition(rebuildFileTemp, 0x44, 0x4, int(textOffsetTableOffset).to_bytes(4, 'little') ) #Add the pointer to the String Offset table 2 to the main table


        #ColumnTypes2
        columnTypes2Offset = len(rebuildFileTemp)
        for column in jsonInfo['COLUMN_NAMES']:
            rebuildFileTemp += data['columnTypes2'][column].to_bytes(1, 'little', signed = True)
        rebuildFileTemp += b'\x00' * calculateSeparator(len(rebuildFileTemp))
        rebuildFileTemp = writeToPosition(rebuildFileTemp, 0x38, 0x4, int(columnTypes2Offset).to_bytes(4, 'little') ) #Add pointer to the main table


        #ColumnTypes
        columnTypesOffset = len(rebuildFileTemp)
        for column in jsonInfo['COLUMN_NAMES']:
            rebuildFileTemp +=  data['columnTypes'][column].to_bytes(1, 'little', signed = True) 
        rebuildFileTemp += b'\x00' * calculateSeparator(len(rebuildFileTemp))
        rebuildFileTemp = writeToPosition(rebuildFileTemp, 0x68, 0x4, int(columnTypesOffset).to_bytes(4, 'little') ) #Add pointer to the main table


        #Column Values
        columnValueOffsets = []
        for column in jsonInfo['COLUMN_NAMES']:
            if data['columnValidity'][column] != "1":
                columnValueOffsets.append(0)
            else:
                columnValueOffsets.append(int(len(rebuildFileTemp)))

                bool_bitmask = '' #Initialize the bool bitmask in case there are boolean columns
                for row in range(0, jsonInfo['ROW_COUNT']):
                    if column not in jsonInfo['ROW_CONTENT'][row]:
                        rebuildFileTemp += b'\xFF\xFF\xFF\xFF'
                    else:

                        if data['columnTypes'][column] == 0: #Int8 unsigned
                            value = jsonInfo['ROW_CONTENT'][row][column]
                            rebuildFileTemp += value.to_bytes(1, 'little', signed = False)

                        elif data['columnTypes'][column] == 1: #Int16 unsigned
                            value = jsonInfo['ROW_CONTENT'][row][column]
                            rebuildFileTemp += value.to_bytes(2, 'little', signed = False)

                        elif data['columnTypes'][column] == 2: #Int32 unsigned
                            value = jsonInfo['ROW_CONTENT'][row][column]
                            rebuildFileTemp += value.to_bytes(4, 'little', signed = False)

                        elif data['columnTypes'][column] == 3: #Int64 unsigned
                            value = jsonInfo['ROW_CONTENT'][row][column]
                            rebuildFileTemp += value.to_bytes(8, 'little', signed = False)

                        elif data['columnTypes'][column] == 4: #Int8 signed
                            value = jsonInfo['ROW_CONTENT'][row][column]
                            rebuildFileTemp += value.to_bytes(1, 'little', signed = True)

                        elif data['columnTypes'][column] == 5: #Int16 signed
                            value = jsonInfo['ROW_CONTENT'][row][column]
                            rebuildFileTemp += value.to_bytes(2, 'little', signed = True)

                        elif data['columnTypes'][column] == 6: #Int32 signed
                            value = jsonInfo['ROW_CONTENT'][row][column]
                            rebuildFileTemp += value.to_bytes(4, 'little', signed = True)

                        elif data['columnTypes'][column] == 7: #Int64 signed
                            value = jsonInfo['ROW_CONTENT'][row][column]
                            rebuildFileTemp += value.to_bytes(8, 'little', signed = True)
                        
                        elif data['columnTypes'][column] == 9: #float32
                            value = jsonInfo['ROW_CONTENT'][row][column]
                            value = bytes(bytearray(struct.pack("<f", value)))
                            rebuildFileTemp += value

                        elif data['columnTypes'][column] == 12: #String
                            index = jsonInfo['TEXT'].index(jsonInfo['ROW_CONTENT'][row][column])
                            rebuildFileTemp += index.to_bytes(4, 'little')

                        elif data['columnTypes'][column] == 11: #Boolean
                            bit = jsonInfo['ROW_CONTENT'][row][column]
                            if len(bool_bitmask) < 8:
                                bool_bitmask += bit
                            if len(bool_bitmask) == 8:
                                bool_bitmask = bool_bitmask[::-1]
                                bool_bitmask = int(bool_bitmask, 2).to_bytes(1, 'little')
                                rebuildFileTemp += bool_bitmask
                                bool_bitmask = ''
                            if row == jsonInfo['ROW_COUNT']-1:
                                bool_bitmask = bool_bitmask.ljust(8, '0')
                                bool_bitmask = bool_bitmask[::-1]
                                bool_bitmask = int(bool_bitmask, 2).to_bytes(1, 'little')
                                rebuildFileTemp += bool_bitmask

        
                rebuildFileTemp += b'\x00' * calculateSeparator(len(rebuildFileTemp))

        

        columnValueOffsetsOffset = len(rebuildFileTemp)
        for offset in columnValueOffsets:
            rebuildFileTemp += offset.to_bytes(4, 'little')
        
        rebuildFileTemp = writeToPosition(rebuildFileTemp, 0x3C, 0x4, int(columnValueOffsetsOffset).to_bytes(4, 'little') ) #Add pointer to the main table


        #Row Index
        rowIndexOffset = int(len(rebuildFileTemp))
        for row in jsonInfo['ROW_NAMES']:
            rebuildFileTemp += jsonInfo['ROW_NAMES'].index(row).to_bytes(4, 'little')
        rebuildFileTemp += b'\x00' * calculateSeparator(len(rebuildFileTemp))
        rebuildFileTemp = writeToPosition(rebuildFileTemp, 0x50, 0x4, int(rowIndexOffset).to_bytes(4, 'little') ) #Add pointer to the main table


        #Column Index
        columnIndexOffset = int(len(rebuildFileTemp))
        for column in jsonInfo['COLUMN_NAMES']:
            rebuildFileTemp += jsonInfo['COLUMN_NAMES'].index(column).to_bytes(4, 'little')
        rebuildFileTemp += b'\x00' * calculateSeparator(len(rebuildFileTemp))
        rebuildFileTemp = writeToPosition(rebuildFileTemp, 0x54, 0x4, int(columnIndexOffset).to_bytes(4, 'little') ) #Add pointer to the main table
            

        #ValidityBool        
        if jsonInfo['HAS_VALIDITYBOOL'] == True:
            validityBoolOffset = len(rebuildFileTemp)
            for row in range(0, jsonInfo['ROW_COUNT']):
                binary = jsonInfo['ROW_CONTENT'][row]['validityBool']
                binary = int(binary, 2).to_bytes(1, 'little')
                rebuildFileTemp += binary
            rebuildFileTemp += b'\x00' * calculateSeparator(len(rebuildFileTemp))
            rebuildFileTemp = writeToPosition(rebuildFileTemp, 0x6C, 0x4, int(validityBoolOffset).to_bytes(4, 'little') ) #Add pointer to the main table
                    


        with open(file_name +'.bin', 'wb') as file:
            file.write(rebuildFileTemp)







file_path = sys.argv[1:][0]
file_name = file_path.split("\\")[-1]
file_extension = file_name.split(".")[-1]


def determineFileExtension(file_extension): #Switch case based on the file extension
    switch = {
        "bin" : exportFile,
        "json" : rebuildFile
    }
    func = switch.get(file_extension.lower(), lambda: "Extension not supported")
    return func()


determineFileExtension(file_extension)
