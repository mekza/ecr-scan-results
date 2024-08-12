SELECT *
FROM ecr_scan_results
WHERE date_parse(time, '%Y-%m-%dT%H:%i:%sZ') > current_date - interval '7' day
ORDER BY time DESC;

--

SELECT
    id,
    detail_type,
    source,
    time,
    repository_name,
    image_digest,
    scan_status,
    severity_undefined,
    severity_low,
    severity_medium,
    severity_high,
    severity_critical,
    image_tags,
    split(image_tags, '|') AS image_tags_array
FROM ecr_scan_results
LIMIT 5;

--

SELECT
    repository_name,
    COUNT(*) AS scan_count,
    SUM(severity_undefined + severity_low + severity_medium + severity_high + severity_critical) AS total_vulnerabilities
FROM ecr_scan_results
GROUP BY repository_name
ORDER BY total_vulnerabilities DESC;

--

SELECT
    repository_name,
    image_digest,
    image_tags,
    severity_critical
FROM ecr_scan_results
WHERE severity_critical > 0
ORDER BY severity_critical DESC;
