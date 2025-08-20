"""Jenkins API client service."""

import os
from typing import Any

import jenkins
from fuzzysearch import find_near_matches


class JenkinsClient(jenkins.Jenkins):
    """Jenkins API client for retrieving build information."""

    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        verify_ssl: bool = True,
    ):
        """Initialize Jenkins client.

        Args:
            url: Jenkins server URL
            username: Jenkins username
            password: Jenkins API token/password
            verify_ssl: Whether to verify SSL certificates
        """
        self.url = url

        if not verify_ssl:
            os.environ["PYTHONHTTPSVERIFY"] = "0"

        super(JenkinsClient, self).__init__(
            url=url,
            username=username,
            password=password,
        )

    def is_connected(self) -> bool:
        """Check if client is connected to Jenkins.

        Returns:
            True if connected, False otherwise
        """
        return self.get_version() is not None

    def list_jobs(self, folder_depth: int = 0) -> list[dict[str, Any]]:
        """List all Jenkins jobs.

        Args:
            folder_depth: Depth to recurse into folders (0 for all)

        Returns:
            List of job information
        """
        return self.get_all_jobs(folder_depth=folder_depth)

    def search_jobs(self, query: str, case_sensitive: bool = False, max_distance: int = 2) -> list[dict[str, Any]]:
        """Search for jobs by name using fuzzy matching with fuzzysearch library.

        Args:
            query: Search query
            case_sensitive: Whether search should be case sensitive
            max_distance: Maximum edit distance for fuzzy matching

        Returns:
            List of matching job information sorted by relevance
        """
        all_jobs = self.list_jobs()
        if not query:
            return all_jobs

        search_query = query if case_sensitive else query.lower()
        matching_jobs = []

        for job in all_jobs:
            job_name = job.get("name", "")
            search_name = job_name if case_sensitive else job_name.lower()

            # Check for different types of matches
            exact_match = search_query == search_name
            contains_match = search_query in search_name
            starts_with_match = search_name.startswith(search_query)

            # Use fuzzysearch for fuzzy matching
            fuzzy_matches = find_near_matches(search_query, search_name, max_l_dist=max_distance)
            fuzzy_match = len(fuzzy_matches) > 0

            if exact_match or contains_match or starts_with_match or fuzzy_match:
                # Calculate relevance score for sorting
                if exact_match:
                    score = 0
                elif starts_with_match:
                    score = 1
                elif contains_match:
                    score = 2
                elif fuzzy_match:
                    # Use the best fuzzy match distance for scoring
                    best_distance = min(match.dist for match in fuzzy_matches)
                    score = 3 + best_distance
                else:
                    score = 100  # Should not happen

                matching_jobs.append((job, score))

        # Sort by relevance score and return just the jobs
        matching_jobs.sort(key=lambda x: x[1])
        return [job for job, score in matching_jobs]

    def get_job_names(self) -> list[str]:
        """Get list of all job names for dropdown.

        Returns:
            List of job names
        """
        jobs = self.list_jobs()
        return [job.get("name", "") for job in jobs if job.get("name")]

    def get_job_builds(self, job_name: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent builds for a job.

        Args:
            job_name: Jenkins job name
            limit: Maximum number of builds to return

        Returns:
            List of build information
        """
        job_info = self.get_job_info(job_name)
        builds = job_info.get("builds", [])

        # Get detailed info for recent builds
        build_details = []
        for build in builds[:limit]:
            try:
                build_info = self.get_build_info(job_name, build["number"])
                build_details.append(build_info)
            except Exception:
                continue

        return build_details
