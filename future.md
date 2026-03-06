Health & Status
moodle admin health - Check Moodle system health

moodle admin status - Display system status (version, plugins, etc.)

moodle admin performance - Show performance metrics and bottlenecks

moodle admin logs system - View system-level logs and errors

moodle admin cron - Trigger and monitor cron jobs

moodle admin tasks - List and manage scheduled tasks

moodle admin cache - Manage cache (purge, status, configuration)

Backup & Restore
moodle backup create <course-id> - Create course backup

moodle backup list - List available backups

moodle backup restore <backup-id> <course-id> - Restore backup to course

moodle backup download <backup-id> - Download backup file

moodle backup schedule - Configure automated backups

moodle backup cleanup - Remove old backup files

moodle backup import - Import backup from external source

System Configuration
moodle config list - List all configuration settings

moodle config get <key> - Get specific configuration value

moodle config set <key> <value> - Update configuration

moodle config export - Export configuration to file

moodle config import <file> - Import configuration from file

moodle config validate - Validate current configuration

👥 User Management (Extended)
Bulk User Operations
moodle users bulk-create <csv-file> - Create multiple users from CSV

moodle users bulk-update <csv-file> - Bulk update user information

moodle users bulk-delete <user-ids-file> - Delete multiple users

moodle users bulk-suspend <user-ids-file> - Suspend multiple users

moodle users bulk-unsuspend <user-ids-file> - Unsuspend multiple users

moodle users bulk-role-assign - Assign roles in bulk

moodle users bulk-import <ldap-file> - Import users from LDAP/CSV

User Analytics
moodle users activity <user-id> - Show user activity timeline

moodle users login-history <user-id> - Display login history

moodle users courses <user-id> - Show enrolled courses with progress

moodle users grades <user-id> - Comprehensive grade report across courses

moodle users completions <user-id> - Completion status across all courses

moodle users certificates <user-id> - List earned certificates

moodle users badges <user-id> - Show earned badges

moodle users cohorts - Manage user cohorts/groups

📚 Course Management (Extended)
Course Analytics
moodle courses analytics <course-id> - Comprehensive course analytics

moodle courses engagement <course-id> - Student engagement metrics

moodle courses activity-heatmap - Visual activity distribution

moodle courses completion-report - Detailed completion statistics

moodle courses grade-distribution - Grade distribution analysis

moodle courses participation - Student participation metrics

moodle courses dropouts - Identify at-risk/dropped students

moodle courses comparison - Compare multiple courses

Course Templates & Import
moodle courses template create <course-id> - Create template from course

moodle courses template list - List available templates

moodle courses template apply <template-id> <course-id> - Apply template

moodle courses import <source-course> <target-course> - Import course content

moodle courses export <course-id> - Export course as template

moodle courses reset <course-id> - Comprehensive course reset options

Course Categorization
moodle categories list - List course categories

moodle categories create <name> - Create new category

moodle categories move <course-id> <category-id> - Move course

moodle categories courses <category-id> - List courses in category

moodle categories hierarchy - Show category tree

moodle categories permissions - Manage category permissions

📝 Content Management
Activity Operations
moodle activities bulk-create - Create multiple activities

moodle activities bulk-delete - Delete multiple activities

moodle activities bulk-move - Move activities between sections

moodle activities duplicate - Duplicate activity within course

moodle activities copy <source-course> <target-course> - Copy to another course

moodle activities reorder - Reorder activities in section

moodle activities settings - View/edit activity settings

moodle activities visibility - Bulk visibility management

moodle activities completion - Bulk completion settings

Resource Management
moodle resources upload - Upload files to course

moodle resources list - List all resources in course

moodle resources download - Download course resources

moodle resources replace - Replace existing resource

moodle resources disk-usage - Show disk usage by course

moodle resources cleanup - Clean unused files

moodle resources quarantine - Quarantine suspicious files

🔐 Security & Access
Role & Permission Management
moodle roles list - List all roles

moodle roles create <name> - Create new role

moodle roles permissions <role-id> - Show role permissions

moodle roles assign <user-id> <role-id> <context> - Assign role

moodle roles unassign <user-id> <role-id> <context> - Remove role

moodle roles export <role-id> - Export role configuration

moodle roles import <file> - Import role configuration

moodle roles capabilities - Search capabilities

Authentication & Security
moodle auth list - List authentication methods

moodle auth enable <method> - Enable auth method

moodle auth disable <method> - Disable auth method

moodle auth test <username> - Test user authentication

moodle sessions list - List active sessions

moodle sessions kill <session-id> - Terminate session

moodle tokens list - List web service tokens

moodle tokens revoke <token-id> - Revoke token

moodle tokens generate <user-id> - Generate new token

moodle security audit - Run security audit

moodle security scan - Scan for vulnerabilities

moodle password-policy - Manage password policies

📈 Reporting & Analytics
Standard Reports
moodle reports course-completion - Course completion report

moodle reports activity-completion - Activity completion report

moodle reports gradebook - Gradebook export

moodle reports participation - Participation report

moodle reports logs - Detailed activity logs

moodle reports statistics - Site statistics

moodle reports certificates - Certificate issuance report

moodle reports badges - Badge awarding report

Custom Reports
moodle reports create - Create custom report

moodle reports save <name> - Save current query as report

moodle reports list - List saved reports

moodle reports run <report-id> - Run saved report

moodle reports schedule - Schedule automated reports

moodle reports export <format> - Export report (PDF, CSV, Excel)

moodle reports dashboard - Create custom dashboard

moodle reports trends - Trend analysis over time

🔧 Plugin Management
moodle plugins list - List all installed plugins

moodle plugins search <keyword> - Search for plugins

moodle plugins install <plugin-name> - Install new plugin

moodle plugins uninstall <plugin-name> - Uninstall plugin

moodle plugins enable <plugin-name> - Enable plugin

moodle plugins disable <plugin-name> - Disable plugin

moodle plugins update - Check for updates

moodle plugins upgrade - Upgrade plugins

moodle plugins dependencies - Show plugin dependencies

moodle plugins conflicts - Check for conflicts

moodle plugins backup - Backup plugin configuration

🌐 Multi-site Management
moodle sites list - List managed Moodle sites

moodle sites add <name> <url> - Add new site to manage

moodle sites switch <site-name> - Switch between sites

moodle sites sync - Sync configuration across sites

moodle sites compare - Compare site configurations

moodle sites migrate - Migrate data between sites

moodle sites status - Status of all managed sites

moodle sites health - Health check all sites

moodle sites backup - Backup all sites

moodle sites batch - Run command across all sites

📱 Integration & Web Services
moodle webservice list - List web services

moodle webservice enable <service> - Enable web service

moodle webservice disable <service> - Disable web service

moodle webservice test <service> - Test web service

moodle api list - List available API functions

moodle api call <function> <params> - Direct API call

moodle api docs <function> - Show API documentation

moodle api rate-limit - Manage rate limiting

moodle api quotas - View/Set API quotas

moodle api logs - View API usage logs

📦 Data Management
Import/Export
moodle data import courses <file> - Import courses

moodle data import users <file> - Import users

moodle data import enrollments <file> - Import enrollments

moodle data import grades <file> - Import grades

moodle data export courses <format> - Export courses

moodle data export users <format> - Export users

moodle data export enrollments <format> - Export enrollments

moodle data export grades <format> - Export grades

Data Cleanup
moodle cleanup unused-courses - Archive/Delete unused courses

moodle cleanup inactive-users - Suspend/Delete inactive users

moodle cleanup temp-files - Clean temporary files

moodle cleanup logs - Rotate/Archive logs

moodle cleanup backups - Clean old backups

moodle cleanup drafts - Clean draft submissions

moodle cleanup orphaned - Clean orphaned data

📋 Audit & Compliance
moodle audit user-actions - Audit user actions

moodle audit grade-changes - Track grade changes

moodle audit enrollments - Enrollment change log

moodle audit configuration - Configuration changes

moodle audit security - Security events log

moodle audit compliance gdpr - GDPR compliance check

moodle audit compliance accessibility - Accessibility audit

moodle audit report <type> - Generate audit report

🚨 Notifications & Alerts
moodle alerts list - List configured alerts

moodle alerts create - Create new alert

moodle alerts test - Test alert system

moodle notifications send - Send notification to users

moodle notifications broadcast - Broadcast message

moodle notifications history - View notification history

moodle notifications templates - Manage notification templates

moodle alerts thresholds - Set alert thresholds

⚙️ Maintenance Mode
moodle maintenance enable - Enable maintenance mode

moodle maintenance disable - Disable maintenance mode

moodle maintenance status - Check maintenance status

moodle maintenance message - Set maintenance message

moodle maintenance schedule - Schedule maintenance

moodle maintenance whitelist - Manage IP whitelist

moodle maintenance tasks - Run maintenance tasks

🎯 Gamification & Engagement
moodle badges list - List available badges

moodle badges award <user-id> <badge-id> - Award badge

moodle badges create - Create new badge

moodle badges criteria - Set badge criteria

moodle certificates list - List certificate templates

moodle certificates issue - Issue certificate

moodle certificates verify <code> - Verify certificate

moodle leaderboard <course-id> - Course leaderboard

moodle points system - Manage points/rewards

📊 Custom Dashboards
moodle dashboard create - Create custom dashboard

moodle dashboard widgets - Manage dashboard widgets

moodle dashboard share - Share dashboard

moodle dashboard export - Export dashboard

moodle dashboard import - Import dashboard

moodle dashboard templates - Dashboard templates

moodle dashboard roles - Role-based dashboards

🔍 Search & Discovery
moodle search index - Rebuild search index

moodle search status - Check search status

moodle search query <term> - Search content

moodle search optimize - Optimize search

moodle search config - Configure search

moodle search stats - Search statistics

moodle search synonyms - Manage search synonyms