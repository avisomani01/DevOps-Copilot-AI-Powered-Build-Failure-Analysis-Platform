ALTER TABLE analyses DROP CONSTRAINT ck_analyses_category;
ALTER TABLE analyses ADD CONSTRAINT ck_analyses_category CHECK (error_category IS NULL OR error_category IN (
    'MAVEN_DEPENDENCY', 'GRADLE_DEPENDENCY', 'JAVA_COMPILATION', 'PYTHON_MODULE', 'DOCKER_BUILD',
    'JENKINS_PIPELINE', 'TEST_FAILURE', 'CONFIGURATION', 'CODE_SYNTAX', 'CODE_REVIEW', 'UNKNOWN'
));

ALTER TABLE analyses DROP CONSTRAINT ck_analyses_analyzer_type;
ALTER TABLE analyses ADD CONSTRAINT ck_analyses_analyzer_type
    CHECK (analyzer_type IS NULL OR analyzer_type IN ('OLLAMA', 'RULE_BASED', 'ML', 'STATIC'));
