-- 先删除可能残留的旧触发器
DROP TRIGGER IF EXISTS TRG_Grade_Calc_Sync;
GO

-- 全新可靠触发器（避免所有语法坑）
CREATE TRIGGER TRG_Grade_Calc_Sync
ON Grade
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;

    -- 第一步：计算单科 Point（只在有插入或更新时执行）
    IF EXISTS (SELECT 1 FROM inserted)
    BEGIN
        UPDATE g
        SET Point = 
            -- 基础绩点
            CASE
                WHEN i.Grade >= 90 THEN 4.0
                WHEN i.Grade >= 85 THEN 3.7
                WHEN i.Grade >= 82 THEN 3.3
                WHEN i.Grade >= 78 THEN 3.0
                WHEN i.Grade >= 75 THEN 2.7
                WHEN i.Grade >= 71 THEN 2.3
                WHEN i.Grade >= 66 THEN 2.0
                WHEN i.Grade >= 62 THEN 1.7
                WHEN i.Grade >= 60 THEN 1.3
                ELSE 0.0
            END
            *
            -- 课程权重（加 TRIM 和 UPPER 防止空格或大小写问题）
            CASE TRIM(UPPER(c.CourseType))
                WHEN '基础必修' THEN 1.2
                WHEN '专业必修' THEN 1.1
                ELSE 1.0
            END
        FROM Grade g
        INNER JOIN inserted i ON g.StudentID = i.StudentID AND g.CourseID = i.CourseID
        INNER JOIN Course c ON g.CourseID = c.CourseID;
    END

    -- 第二步：收集受影响的学生ID
    DECLARE @Affected TABLE (StudentID VARCHAR(20));

    INSERT INTO @Affected (StudentID)
    SELECT StudentID FROM inserted
    UNION
    SELECT StudentID FROM deleted;

    -- 第三步：如果有受影响的学生，才重新计算 TotalGPA
    IF EXISTS (SELECT 1 FROM @Affected)
    BEGIN
        UPDATE s
        SET TotalGPA = ISNULL((
            SELECT CAST(
                SUM(c.Credits * ISNULL(g.Point, 0.0)) / NULLIF(SUM(c.Credits), 0) 
                AS DECIMAL(10,2)
            )
            FROM Grade g
            INNER JOIN Course c ON g.CourseID = c.CourseID
            WHERE g.StudentID = s.StudentID
        ), 0.00)
        FROM Student s
        WHERE s.StudentID IN (SELECT StudentID FROM @Affected);
    END
END
GO