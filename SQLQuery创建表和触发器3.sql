-- File: database_schema.sql
-- Functionality: SQL script to create the SchoolDB database, tables, and triggers. Optimized for performance and added indexes where useful.

USE master;
GO
CREATE DATABASE SchoolDB2;
GO
USE SchoolDB2;
GO

-- Department Table
CREATE TABLE Department (
    DeptID VARCHAR(20) PRIMARY KEY,
    DeptName VARCHAR(50) NOT NULL,
    Telephone VARCHAR(20)
);
GO

-- Class Table
CREATE TABLE Class (
    ClassID VARCHAR(20) PRIMARY KEY,
    ClassName VARCHAR(50) NOT NULL,
    DeptID VARCHAR(20),
    FOREIGN KEY (DeptID) REFERENCES Department(DeptID)
);
GO

-- UserInfo Table
CREATE TABLE UserInfo (
    UserID VARCHAR(20) PRIMARY KEY,
    Username VARCHAR(50) NOT NULL UNIQUE,
    Password VARCHAR(100) NOT NULL,
    UserType VARCHAR(10) CHECK (UserType IN ('Student','Teacher','Admin'))
);
GO

-- Student Table
CREATE TABLE Student (
    StudentID VARCHAR(20) PRIMARY KEY,
    StudentName VARCHAR(50) NOT NULL,
    Gender VARCHAR(10),
    ClassID VARCHAR(20),
    UserID VARCHAR(20),
    TotalGPA DECIMAL(10, 2) DEFAULT 0.0,
    FOREIGN KEY (ClassID) REFERENCES Class(ClassID),
    FOREIGN KEY (UserID) REFERENCES UserInfo(UserID)
);
GO

-- Teacher Table
CREATE TABLE Teacher (
    TeacherID VARCHAR(20) PRIMARY KEY,
    TeacherName VARCHAR(50) NOT NULL,
    Phone VARCHAR(20),
    DeptID VARCHAR(20),
    UserID VARCHAR(20),
    FOREIGN KEY (DeptID) REFERENCES Department(DeptID),
    FOREIGN KEY (UserID) REFERENCES UserInfo(UserID)
);
GO

-- ClassRoom Table
CREATE TABLE ClassRoom (
    ClassRoomID VARCHAR(20) PRIMARY KEY,
    Building VARCHAR(50),
    Floor INT,
    Capacity INT,
    LocationX DECIMAL(10, 2),
    LocationY DECIMAL(10, 2)
);
GO

-- Course Table
CREATE TABLE Course (
    CourseID VARCHAR(20) PRIMARY KEY,
    CourseName VARCHAR(100) NOT NULL,
    CourseType VARCHAR(20),
    Credits DECIMAL(3, 1) DEFAULT 2.0,
    MaxStudents INT CHECK (MaxStudents > 0)
);
GO

-- TeacherCourse Table
CREATE TABLE TeacherCourse (
    TeacherID VARCHAR(20),
    CourseID VARCHAR(20),
    IsMain BIT DEFAULT 0,
    PRIMARY KEY (TeacherID, CourseID),
    FOREIGN KEY (TeacherID) REFERENCES Teacher(TeacherID),
    FOREIGN KEY (CourseID) REFERENCES Course(CourseID)
);
GO

-- CourseSchedule Table
CREATE TABLE CourseSchedule (
    ScheduleID INT IDENTITY(1,1) PRIMARY KEY,
    CourseID VARCHAR(20),
    TeacherID VARCHAR(20),
    ClassRoomID VARCHAR(20),
    WeekDay INT CHECK (WeekDay BETWEEN 1 AND 7),
    StartTime TIME,
    EndTime TIME,
    FOREIGN KEY (CourseID) REFERENCES Course(CourseID),
    FOREIGN KEY (TeacherID) REFERENCES Teacher(TeacherID),
    FOREIGN KEY (ClassRoomID) REFERENCES ClassRoom(ClassRoomID)
);
GO

-- StudentCourse Table
CREATE TABLE StudentCourse (
    StudentID VARCHAR(20),
    CourseID VARCHAR(20),
    PRIMARY KEY (StudentID, CourseID),
    FOREIGN KEY (StudentID) REFERENCES Student(StudentID),
    FOREIGN KEY (CourseID) REFERENCES Course(CourseID)
);
GO

-- Grade Table
CREATE TABLE Grade (
    StudentID VARCHAR(20),
    CourseID VARCHAR(20),
    Grade DECIMAL(5, 2),
    Point DECIMAL(4, 2),
    PRIMARY KEY (StudentID, CourseID),
    FOREIGN KEY (StudentID) REFERENCES Student(StudentID),
    FOREIGN KEY (CourseID) REFERENCES Course(CourseID)
);
GO

-- Nodes Table (for Map)
CREATE TABLE Nodes (
    NodeID NVARCHAR(10) PRIMARY KEY,
    X INT NOT NULL,
    Y INT NOT NULL,
    Name NVARCHAR(50) NULL
);
GO

-- Edges Table (for Map)
CREATE TABLE Edges (
    EdgeID INT IDENTITY(1,1) PRIMARY KEY,
    FromNode NVARCHAR(10) NOT NULL,
    ToNode NVARCHAR(10) NOT NULL,
    FOREIGN KEY (FromNode) REFERENCES Nodes(NodeID),
    FOREIGN KEY (ToNode) REFERENCES Nodes(NodeID)
);
GO

-- Indexes for performance
CREATE INDEX IDX_StudentCourse_StudentID ON StudentCourse(StudentID);
CREATE INDEX IDX_StudentCourse_CourseID ON StudentCourse(CourseID);
CREATE INDEX IDX_Grade_StudentID ON Grade(StudentID);
CREATE INDEX IDX_CourseSchedule_CourseID ON CourseSchedule(CourseID);

-- Triggers (optimized and kept essential ones)

-- Trigger: CourseSchedule Time Check
CREATE OR ALTER TRIGGER TRG_CourseSchedule_TimeCheck
ON CourseSchedule
FOR INSERT, UPDATE
AS
BEGIN
    IF EXISTS (SELECT 1 FROM inserted WHERE StartTime >= EndTime)
    BEGIN
        RAISERROR('开始时间不能晚于或等于结束时间！', 16, 1);
        ROLLBACK TRANSACTION;
    END
END;
GO

-- Trigger: StudentCourse Max Limit (simplified to use trigger on insert)
CREATE OR ALTER TRIGGER TRG_StudentCourse_MaxLimit
ON StudentCourse
FOR INSERT
AS
BEGIN
    DECLARE @CourseID VARCHAR(20), @Count INT, @Max INT;
    SELECT @CourseID = CourseID FROM inserted;
    SELECT @Count = COUNT(*) FROM StudentCourse WHERE CourseID = @CourseID;
    SELECT @Max = MaxStudents FROM Course WHERE CourseID = @CourseID;
    IF @Count > @Max
    BEGIN
        RAISERROR('该课程选课人数已满！', 16, 1);
        ROLLBACK TRANSACTION;
    END
END;
GO

-- Trigger: Grade Calc and Sync (optimized for batch operations)
CREATE OR ALTER TRIGGER TRG_Grade_Calc_Sync
ON Grade
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    -- Calculate Point for inserted/updated
    IF EXISTS (SELECT 1 FROM inserted)
    BEGIN
        UPDATE G
        SET Point = 
            (CASE
                WHEN I.Grade >= 90 THEN 4.0
                WHEN I.Grade >= 85 THEN 3.7
                WHEN I.Grade >= 82 THEN 3.3
                WHEN I.Grade >= 78 THEN 3.0
                WHEN I.Grade >= 75 THEN 2.7
                WHEN I.Grade >= 71 THEN 2.3
                WHEN I.Grade >= 66 THEN 2.0
                WHEN I.Grade >= 62 THEN 1.7
                WHEN I.Grade >= 60 THEN 1.3
                ELSE 0.0
            END) * 
            (CASE C.CourseType
                WHEN '基础必修' THEN 1.2
                WHEN '专业必修' THEN 1.1
                WHEN '选修' THEN 1.0
                ELSE 1.0
            END)
        FROM Grade G
        JOIN inserted I ON G.StudentID = I.StudentID AND G.CourseID = I.CourseID
        JOIN Course C ON G.CourseID = C.CourseID;
    END
    -- Update TotalGPA for affected students
    WITH Affected AS (
        SELECT StudentID FROM inserted
        UNION
        SELECT StudentID FROM deleted
    )
    UPDATE S
    SET TotalGPA = ISNULL((
        SELECT CAST(SUM(C.Credits * G.Point) / NULLIF(SUM(C.Credits), 0) AS DECIMAL(10, 2))
        FROM Grade G JOIN Course C ON G.CourseID = C.CourseID
        WHERE G.StudentID = S.StudentID
    ), 0)
    FROM Student S JOIN Affected A ON S.StudentID = A.StudentID;
END;
GO

-- Trigger: Course Update Sync GPA
CREATE OR ALTER TRIGGER TRG_Course_Update_SyncGPA
ON Course
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    IF (UPDATE(Credits) OR UPDATE(CourseType))
    BEGIN
        IF UPDATE(CourseType)
        BEGIN
            DISABLE TRIGGER TRG_Grade_Calc_Sync ON Grade;
            UPDATE G
            SET G.Point = 
                (CASE
                    WHEN G.Grade >= 90 THEN 4.0
                    WHEN G.Grade >= 85 THEN 3.7
                    WHEN G.Grade >= 82 THEN 3.3
                    WHEN G.Grade >= 78 THEN 3.0
                    WHEN G.Grade >= 75 THEN 2.7
                    WHEN G.Grade >= 71 THEN 2.3
                    WHEN G.Grade >= 66 THEN 2.0
                    WHEN G.Grade >= 62 THEN 1.7
                    WHEN G.Grade >= 60 THEN 1.3
                    ELSE 0.0
                END) * 
                (CASE i.CourseType
                    WHEN '基础必修' THEN 1.2
                    WHEN '专业必修' THEN 1.1
                    WHEN '选修' THEN 1.0
                    ELSE 1.0
                END)
            FROM Grade G JOIN inserted i ON G.CourseID = i.CourseID;
            ENABLE TRIGGER TRG_Grade_Calc_Sync ON Grade;
        END
        WITH Affected AS (
            SELECT DISTINCT StudentID FROM Grade WHERE CourseID IN (SELECT CourseID FROM inserted)
        )
        UPDATE s
        SET TotalGPA = ISNULL((
            SELECT CAST(SUM(c.Credits * G.Point) / NULLIF(SUM(c.Credits), 0) AS DECIMAL(10, 2))
            FROM Grade G JOIN Course c ON G.CourseID = c.CourseID
            WHERE G.StudentID = s.StudentID
        ), 0)
        FROM Student s JOIN Affected A ON s.StudentID = A.StudentID;
    END
END;
GO