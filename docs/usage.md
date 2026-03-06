# moodlectl CLI Documentation

## Overview

`moodlectl` is a headless LMS CLI tool for Moodle that provides comprehensive management capabilities through a command-line interface. It's built using Python with Typer for CLI handling and Rich for beautiful terminal output.

## Installation & Setup

### Prerequisites
- Python 3.8+
- Moodle instance with web services enabled
- API credentials configured

### Configuration
Create a `.env` file or set environment variables:
```bash
MOODLE_URL=https://your-moodle-instance.com
MOODLE_TOKEN=your_webservice_token
MOODLE_API_FORMAT=json
LOG_LEVEL=INFO
LOG_FORMAT=text
```

## Command Structure

```
moodlectl [OPTIONS] COMMAND [ARGS]...
```

### Global Options
| Option | Description |
|--------|-------------|
| `--verbose, -v` | Enable verbose output |
| `--log-format [json\|text]` | Override log format |

### Available Commands
- `courses` - Course management
- `enrollments` - Enrollment management
- `grades` - Grade management
- `progress` - Progress tracking
- `users` - User management
- `logs` - Activity log commands

---

## Course Management (`courses`)

### List Courses
```bash
moodlectl courses list [OPTIONS]
```

**Options:**
- `--category-id, -c INTEGER` - Filter by category
- `--format [table\|json\|csv]` - Output format (default: table)
- `--verbose, -v` - Show extended fields

**Example:**
```bash
moodlectl courses list --category-id 5 --format table
```

### Get Course Details
```bash
moodlectl courses get COURSE_ID [--format table|json]
```

**Example:**
```bash
moodlectl courses get 123 --format json
```

### Create Course
```bash
moodlectl courses create --shortname CS101 --fullname "Computer Science 101" --category-id 5
```

### Update Course
```bash
moodlectl courses update COURSE_ID [--fullname "New Name"] [--visible|--hidden]
```

### Duplicate Course
```bash
moodlectl courses duplicate SOURCE_ID --new-shortname CS101-2024 --new-fullname "CS101 2024 Edition"
```

### Archive Course
```bash
moodlectl courses archive COURSE_ID [--category-id ARCHIVE_CAT] [--dry-run]
```

### Show Course Structure
```bash
moodlectl courses structure COURSE_ID [--format tree|json]
```

### Reset Course
```bash
moodlectl courses reset COURSE_ID [OPTIONS] [--dry-run]
```

**Reset Options:**
- `--reset-grades` - Reset all grades
- `--reset-completions` - Reset completion data
- `--reset-submissions` - Reset assignment submissions
- `--reset-quizzes` - Reset quiz attempts
- `--reset-forums` - Delete forum posts
- `--all` - Reset everything

---

## User Management (`users`)

### Get User by ID
```bash
moodlectl users get USER_ID [--format table|json]
```

### Search Users
```bash
moodlectl users search --query "john" [--limit 50] [--format table|json]
```

### Find User by Email
```bash
moodlectl users find-by-email user@example.com [--format table|json]
```

### Get User Roles
```bash
moodlectl users roles USER_ID --course-id COURSE_ID [--format table|json]
```

---

## Enrollment Management (`enrollments`)

### List Enrollments
```bash
moodlectl enrollments list COURSE_ID [--format table|json|csv]
```

### Add Enrollment
```bash
moodlectl enrollments add USER_ID COURSE_ID [--role-id ROLE_ID] [--dry-run]
```
*Note: Default role_id=5 (student), 3=teacher*

### Remove Enrollment
```bash
moodlectl enrollments remove USER_ID COURSE_ID [--dry-run]
```

### Bulk Enroll
```bash
moodlectl enrollments bulk --file enrollments.csv [--dry-run]
```

**CSV Format:**
```csv
user_id,course_id,role_id
123,101,5
456,101,3
```

### Sync Enrollments
```bash
moodlectl enrollments sync COURSE_ID --file expected_enrollments.csv [--dry-run]
```

---

## Grade Management (`grades`)

### Grade Report
```bash
moodlectl grades report COURSE_ID [--user-id USER_ID] [--format table|json|csv]
```

### Grade Distribution
```bash
moodlectl grades distribution COURSE_ID [--format table|json]
```
Shows mean, median, standard deviation, and grade buckets.

### Student Performance
```bash
moodlectl grades performance COURSE_ID [--format table|json]
```
Shows ranked students with z-scores, percentiles, and performance bands (A-F).

---

## Progress Tracking (`progress`)

### User Progress Report
```bash
moodlectl progress report USER_ID [--course-id COURSE_ID] [--format table|json]
```

### Course Completion Statistics
```bash
moodlectl progress completion COURSE_ID [--format table|json]
```

### Identify At-Risk Users
```bash
moodlectl progress at-risk COURSE_ID [--threshold 0.3] [--format table|json]
```
*Note: threshold is a decimal (0.0-1.0) representing completion percentage*

---

## Activity Logs (`logs`)

### Course Activity Logs
```bash
moodlectl logs course COURSE_ID [--since YYYY-MM-DD] [--limit 100] [--format table|json]
```

### User Activity Logs
```bash
moodlectl logs user USER_ID [--course-id COURSE_ID] [--since YYYY-MM-DD] [--format table|json]
```

### Activity Hotspots
```bash
moodlectl logs hotspots COURSE_ID [--since YYYY-MM-DD] [--format table|json]
```
Identifies most accessed activities in a course.

---

## Output Formats

All commands support multiple output formats:

### Table Format (Default)
Rich formatted tables with colors and alignment.

### JSON Format
```bash
--format json
```
Machine-readable JSON output.

### CSV Format
```bash
--format csv
```
Comma-separated values for spreadsheet import.

---

## Dry Run Mode

Many destructive commands support `--dry-run` to preview changes:
```bash
moodlectl enrollments add 123 101 --dry-run
moodlectl courses archive 456 --dry-run
moodlectl courses reset 789 --all --dry-run
```

---

## Error Handling

- Commands exit with non-zero code on error
- Error messages are printed to stderr in red
- Use `--verbose` for detailed debugging output

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MOODLE_URL` | Moodle instance URL | Required |
| `MOODLE_TOKEN` | Web service token | Required |
| `MOODLE_API_FORMAT` | API format | `json` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `LOG_FORMAT` | Log format | `text` |

---

## Example Workflows

### 1. Create Course and Enroll Students
```bash
# Create course
moodlectl courses create --shortname PY101 --fullname "Python Programming" --category-id 10

# Get course ID (assume it's 123)
# Bulk enroll students
moodlectl enrollments bulk --file students.csv

# Verify enrollments
moodlectl enrollments list 123
```

### 2. Monitor Student Progress
```bash
# Check overall progress
moodlectl progress completion 123

# Identify struggling students
moodlectl progress at-risk 123 --threshold 0.4

# Check individual student
moodlectl progress report 456 --course-id 123
```

### 3. Grade Analysis
```bash
# Get full grade report
moodlectl grades report 123

# View distribution
moodlectl grades distribution 123

# Rank students
moodlectl grades performance 123
```

### 4. Audit Activity
```bash
# Get recent course activity
moodlectl logs course 123 --since 2024-01-01

# Check specific student
moodlectl logs user 456 --course-id 123

# Find popular activities
moodlectl logs hotspots 123
```

### 5. Course Reset for New Term
```bash
# Archive old course
moodlectl courses archive 123 --category-id 999

# Duplicate for new term
moodlectl courses duplicate 123 \
  --new-shortname PY101-2024 \
  --new-fullname "Python Programming 2024"

# Reset data in new course (ID: 124)
moodlectl courses reset 124 --all
```

---

## Exit Codes

| Code | Description |
|------|-------------|
| `0` | Success |
| `1` | General error |
| `2` | Configuration error |
| `3` | API error |

---

## Notes & Limitations

- Rate limiting is handled automatically
- Some operations may take time for large courses
- JSON output uses `model_dump(mode="json")` for proper datetime serialization
- Bulk operations have built-in error handling with partial success reporting