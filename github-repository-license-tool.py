#!/usr/bin/env python3
"""
GitHub Repository Finder for George Washington University Students
This script searches for open source repositories from GWU students/affiliates.
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import argparse


class GitHubRepoFinder:
    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize the GitHub repository finder.
        
        Args:
            github_token: GitHub personal access token for higher rate limits
        """
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GWU-Repo-Finder"
        }
        
        if github_token:
            self.headers["Authorization"] = f"token {github_token}"
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Calculate 6 months ago
        self.six_months_ago = datetime.now() - timedelta(days=180)
    
    def search_gw_users(self) -> List[Dict]:
        """
        Search for GitHub users affiliated with George Washington University.
        """
        print("Searching for George Washington University users...")
        
        # Different search queries to find GW users
        search_queries = [
            "George Washington University",
            "GWU",
            "gwu.edu",
            '"George Washington University"',
            "location:Washington location:DC George Washington"
        ]
        
        all_users = []
        seen_users = set()
        
        for query in search_queries:
            try:
                url = f"{self.base_url}/search/users"
                params = {
                    "q": query,
                    "per_page": 100
                }
                
                response = self.session.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                users = data.get("items", [])
                
                for user in users:
                    if user["login"] not in seen_users:
                        seen_users.add(user["login"])
                        all_users.append(user)
                
                print(f"Found {len(users)} users for query: {query}")
                time.sleep(1)  # Rate limiting
                
            except requests.exceptions.RequestException as e:
                print(f"Error searching users with query '{query}': {e}")
                continue
        
        print(f"Total unique users found: {len(all_users)}")
        return all_users
    
    def get_user_repos(self, username: str) -> List[Dict]:
        """
        Get all public repositories for a given user.
        """
        try:
            url = f"{self.base_url}/users/{username}/repos"
            params = {
                "type": "public",
                "per_page": 100,
                "sort": "updated"
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            repos = response.json()
            return repos
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching repos for {username}: {e}")
            return []
    
    def check_license_file(self, owner: str, repo: str) -> bool:
        """
        Check if repository has LICENSE or COPYING file in root directory.
        """
        license_files = ["LICENSE", "COPYING", "LICENSE.txt", "LICENSE.md", 
                        "COPYING.txt", "COPYING.md", "license", "copying"]
        
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/contents"
            response = self.session.get(url)
            response.raise_for_status()
            
            contents = response.json()
            file_names = [item["name"] for item in contents if item["type"] == "file"]
            
            return any(license_file in file_names for license_file in license_files)
            
        except requests.exceptions.RequestException:
            return False
    
    def check_recent_activity(self, owner: str, repo: str) -> Dict[str, bool]:
        """
        Check if repository has recent commits and issues within 6 months.
        """
        activity = {"recent_commits": False, "recent_issues": False}
        
        # Check recent commits
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/commits"
            params = {"per_page": 10, "since": self.six_months_ago.isoformat()}
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            commits = response.json()
            activity["recent_commits"] = len(commits) > 0
            
        except requests.exceptions.RequestException:
            pass
        
        # Check recent issues
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/issues"
            params = {
                "state": "all",
                "per_page": 10,
                "since": self.six_months_ago.isoformat()
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            issues = response.json()
            activity["recent_issues"] = len(issues) > 0
            
        except requests.exceptions.RequestException:
            pass
        
        return activity
    
    def is_repo_active(self, activity: Dict[str, bool]) -> bool:
        """
        Determine if repository is active based on recent commits and issues.
        """
        return activity["recent_commits"] or activity["recent_issues"]
    
    def analyze_repository(self, repo: Dict) -> Optional[Dict]:
        """
        Analyze a single repository for open source criteria and activity.
        """
        owner = repo["owner"]["login"]
        repo_name = repo["name"]
        
        print(f"Analyzing {owner}/{repo_name}...")
        
        # Check for license file
        has_license = self.check_license_file(owner, repo_name)
        if not has_license:
            return None
        
        # Check recent activity
        activity = self.check_recent_activity(owner, repo_name)
        if not self.is_repo_active(activity):
            return None
        
        # Repository meets criteria
        result = {
            "owner": owner,
            "repository name": repo_name,
            "full_name": repo["full_name"],
            "description": repo.get("description", "No description"),
            "html_url": repo["html_url"],
            "language": repo.get("language", "Unknown"),
            "stars": repo["stargazers_count"],
            "forks": repo["forks_count"],
            "updated_at": repo["updated_at"],
            "has_license": has_license,
            "recent_commits": activity["recent_commits"],
            "recent_issues": activity["recent_issues"]
        }
        
        return result
    
    def find_open_source_repos(self, max_users: Optional[int] = None) -> List[Dict]:
        """
        Main method to find open source repositories from GW users.
        """
        # Find GW users
        users = self.search_gw_users()
        
        if max_users:
            users = users[:max_users]
        
        open_source_repos = []
        
        for i, user in enumerate(users, 1):
            username = user["login"]
            print(f"\nProcessing user {i}/{len(users)}: {username}")
            
            # Get user's repositories
            repos = self.get_user_repos(username)
            
            for repo in repos:
                # Skip forks unless specified otherwise
                if repo["fork"]:
                    continue
                
                result = self.analyze_repository(repo)
                if result:
                    open_source_repos.append(result)
                    print(f"✓ Found qualifying repo: {result['full_name']}")
                
                time.sleep(0.5)  # Rate limiting
            
            time.sleep(1)  # Rate limiting between users
        
        return open_source_repos
    
    def save_results(self, repos: List[Dict], filename: str = "gw_open_source_repos.json"):
        """
        Save results to a JSON file.
        """
        with open(filename, 'w') as f:
            json.dump(repos, f, indent=2, default=str)
        print(f"\nResults saved to {filename}")
    
    def print_summary(self, repos: List[Dict]):
        """
        Print a summary of found repositories.
        """
        print(f"\n{'='*60}")
        print(f"SUMMARY: Found {len(repos)} qualifying repositories")
        print(f"{'='*60}")
        
        for repo in repos:
            print(f"\n📦 {repo['full_name']}")
            print(f"   🔗 {repo['html_url']}")
            print(f"   📝 {repo['description'][:100]}...")
            print(f"   💻 Language: {repo['language']}")
            print(f"   ⭐ Stars: {repo['stars']} | 🍴 Forks: {repo['forks']}")
            print(f"   📅 Last updated: {repo['updated_at']}")
            print(f"   ✅ Recent commits: {repo['recent_commits']}")
            print(f"   🐛 Recent issues: {repo['recent_issues']}")


def main():
    #Load environment variables from .env file
    with open(".env") as config_file:
        config = json.load(config_file)
    
    github_token = config.get("githubtoken")

    parser = argparse.ArgumentParser(
        description="Find open source repositories from George Washington University students"
    )
    
    parser.add_argument(
        "--max-users", 
        type=int, 
        help="Maximum number of users to analyze (for testing)"
    )
    parser.add_argument(
        "--output", 
        default="gw_open_source_repos.json",
        help="Output filename for results (default: gw_open_source_repos.json)"
    )
    
    args = parser.parse_args()
    
    if not github_token:
        print("⚠️  Warning: No GitHub token provided. Rate limits will be lower.")
        print("   Create a token at: https://github.com/settings/tokens")
        print("   Then run with: python script.py --token YOUR_TOKEN\n")
    
    # Initialize finder
    finder = GitHubRepoFinder(github_token)
    
    try:
        # Find repositories
        repos = finder.find_open_source_repos(args.max_users)
        
        # Save and display results
        finder.save_results(repos, args.output)
        finder.print_summary(repos)
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()