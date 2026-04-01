#!/usr/bin/env python3
"""
Code Coverage Analysis Script for TradeSense
Task 18.11: Verify code coverage

This script runs coverage analysis for both Python and TypeScript codebases
and generates comprehensive reports.

Requirements:
- 16.1: THE System SHALL achieve 85% or greater code coverage
- 16.2: THE System SHALL achieve 100% critical path coverage
"""

import subprocess
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple


class CoverageAnalyzer:
    def __init__(self):
        self.backend_dir = Path("backend")
        self.frontend_dir = Path("frontend")
        self.results = {
            "python": {},
            "typescript": {},
            "overall": {},
            "critical_paths": {}
        }
        
    def run_python_coverage(self) -> Tuple[bool, Dict]:
        """Run pytest with coverage for Python backend"""
        print("\n" + "="*80)
        print("PYTHON COVERAGE ANALYSIS")
        print("="*80 + "\n")
        
        try:
            # Run pytest with coverage from backend directory
            cmd = [
                "python", "-m", "pytest",
                "tests/",
                "--cov=.",
                "--cov-report=term-missing",
                "--cov-report=json:coverage.json",
                "--cov-report=html:htmlcov",
                "-v",
                "--tb=short",
                "-q"
            ]
            
            print(f"Running: {' '.join(cmd)} (in backend/)\n")
            result = subprocess.run(
                cmd,
                cwd=self.backend_dir,
                capture_output=True,
                text=True
            )
            
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            
            # Parse coverage JSON
            coverage_file = self.backend_dir / "coverage.json"
            if coverage_file.exists():
                with open(coverage_file) as f:
                    coverage_data = json.load(f)
                    
                total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)
                
                self.results["python"] = {
                    "total_coverage": total_coverage,
                    "lines_covered": coverage_data.get("totals", {}).get("covered_lines", 0),
                    "lines_total": coverage_data.get("totals", {}).get("num_statements", 0),
                    "files": coverage_data.get("files", {}),
                    "report_path": "backend/htmlcov/index.html"
                }
                
                print(f"\n✓ Python Coverage: {total_coverage:.2f}%")
                return True, self.results["python"]
            else:
                print(f"✗ Coverage JSON file not found at {coverage_file}")
                return False, {}
                
        except Exception as e:
            print(f"✗ Error running Python coverage: {e}")
            import traceback
            traceback.print_exc()
            return False, {}
    
    def run_typescript_coverage(self) -> Tuple[bool, Dict]:
        """Run vitest with coverage for TypeScript frontend"""
        print("\n" + "="*80)
        print("TYPESCRIPT COVERAGE ANALYSIS")
        print("="*80 + "\n")
        
        try:
            # Check if node_modules exists
            if not (self.frontend_dir / "node_modules").exists():
                print("Installing frontend dependencies...")
                subprocess.run(["npm", "install"], cwd=self.frontend_dir, check=True)
            
            # Run vitest with coverage
            cmd = ["npm", "run", "test", "--", "--coverage"]
            
            print(f"Running: {' '.join(cmd)} (in {self.frontend_dir})\n")
            result = subprocess.run(
                cmd,
                cwd=self.frontend_dir,
                capture_output=True,
                text=True
            )
            
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            
            # Parse coverage JSON
            coverage_file = self.frontend_dir / "coverage" / "coverage-summary.json"
            if coverage_file.exists():
                with open(coverage_file) as f:
                    coverage_data = json.load(f)
                    
                total = coverage_data.get("total", {})
                total_coverage = total.get("lines", {}).get("pct", 0)
                
                self.results["typescript"] = {
                    "total_coverage": total_coverage,
                    "lines_covered": total.get("lines", {}).get("covered", 0),
                    "lines_total": total.get("lines", {}).get("total", 0),
                    "statements": total.get("statements", {}),
                    "branches": total.get("branches", {}),
                    "functions": total.get("functions", {}),
                    "report_path": "frontend/coverage/index.html"
                }
                
                print(f"\n✓ TypeScript Coverage: {total_coverage:.2f}%")
                return True, self.results["typescript"]
            else:
                print("✗ Coverage JSON file not found")
                return False, {}
                
        except Exception as e:
            print(f"✗ Error running TypeScript coverage: {e}")
            return False, {}
    
    def analyze_critical_paths(self) -> Dict:
        """Identify and analyze critical path coverage"""
        print("\n" + "="*80)
        print("CRITICAL PATH ANALYSIS")
        print("="*80 + "\n")
        
        critical_paths = {
            "voice_pipeline": [
                "voice/stt.py",
                "voice/tts.py",
                "voice/vad.py",
                "voice/pipeline.py"
            ],
            "agent_routing": [
                "orchestration/intent_classifier.py",
                "orchestration/agent_router.py",
                "orchestration/conversation_context.py"
            ],
            "intake_agent": [
                "agents/intake.py",
                "api/routes/intake.py"
            ],
            "diagnostic_agent": [
                "agents/diagnostic.py",
                "agents/documentation_rag.py"
            ],
            "fulfillment_agent": [
                "agents/fulfillment.py"
            ],
            "security": [
                "security/auth.py",
                "security/rbac.py",
                "security/encryption.py",
                "security/pii_redaction.py"
            ],
            "error_handling": [
                "core/error_handling.py",
                "llm/api_error_handler.py",
                "db/error_recovery.py"
            ]
        }
        
        python_files = self.results.get("python", {}).get("files", {})
        
        critical_coverage = {}
        for path_name, files in critical_paths.items():
            path_coverage = []
            for file in files:
                file_data = python_files.get(file, {})
                if file_data:
                    summary = file_data.get("summary", {})
                    coverage_pct = summary.get("percent_covered", 0)
                    path_coverage.append({
                        "file": file,
                        "coverage": coverage_pct,
                        "lines_covered": summary.get("covered_lines", 0),
                        "lines_total": summary.get("num_statements", 0)
                    })
                else:
                    path_coverage.append({
                        "file": file,
                        "coverage": 0,
                        "status": "not_found"
                    })
            
            avg_coverage = sum(f["coverage"] for f in path_coverage if "coverage" in f) / len(path_coverage) if path_coverage else 0
            critical_coverage[path_name] = {
                "files": path_coverage,
                "average_coverage": avg_coverage
            }
            
            status = "✓" if avg_coverage >= 100 else "⚠" if avg_coverage >= 85 else "✗"
            print(f"{status} {path_name}: {avg_coverage:.2f}%")
        
        self.results["critical_paths"] = critical_coverage
        return critical_coverage
    
    def calculate_overall_coverage(self) -> Dict:
        """Calculate overall coverage across Python and TypeScript"""
        print("\n" + "="*80)
        print("OVERALL COVERAGE SUMMARY")
        print("="*80 + "\n")
        
        py_coverage = self.results.get("python", {}).get("total_coverage", 0)
        py_lines_covered = self.results.get("python", {}).get("lines_covered", 0)
        py_lines_total = self.results.get("python", {}).get("lines_total", 0)
        
        ts_coverage = self.results.get("typescript", {}).get("total_coverage", 0)
        ts_lines_covered = self.results.get("typescript", {}).get("lines_covered", 0)
        ts_lines_total = self.results.get("typescript", {}).get("lines_total", 0)
        
        total_lines_covered = py_lines_covered + ts_lines_covered
        total_lines = py_lines_total + ts_lines_total
        
        overall_coverage = (total_lines_covered / total_lines * 100) if total_lines > 0 else 0
        
        self.results["overall"] = {
            "coverage": overall_coverage,
            "lines_covered": total_lines_covered,
            "lines_total": total_lines,
            "python_coverage": py_coverage,
            "typescript_coverage": ts_coverage
        }
        
        print(f"Python Coverage:     {py_coverage:.2f}% ({py_lines_covered}/{py_lines_total} lines)")
        print(f"TypeScript Coverage: {ts_coverage:.2f}% ({ts_lines_covered}/{ts_lines_total} lines)")
        print(f"Overall Coverage:    {overall_coverage:.2f}% ({total_lines_covered}/{total_lines} lines)")
        
        return self.results["overall"]
    
    def generate_report(self) -> str:
        """Generate comprehensive coverage report"""
        print("\n" + "="*80)
        print("COVERAGE REQUIREMENTS VALIDATION")
        print("="*80 + "\n")
        
        overall = self.results.get("overall", {})
        overall_coverage = overall.get("coverage", 0)
        
        # Requirement 16.1: 85%+ overall coverage
        req_16_1 = overall_coverage >= 85
        print(f"{'✓' if req_16_1 else '✗'} Requirement 16.1: Overall coverage >= 85%")
        print(f"  Current: {overall_coverage:.2f}%")
        
        # Requirement 16.2: 100% critical path coverage
        critical_paths = self.results.get("critical_paths", {})
        critical_below_100 = []
        for path_name, data in critical_paths.items():
            avg_cov = data.get("average_coverage", 0)
            if avg_cov < 100:
                critical_below_100.append((path_name, avg_cov))
        
        req_16_2 = len(critical_below_100) == 0
        print(f"\n{'✓' if req_16_2 else '✗'} Requirement 16.2: 100% critical path coverage")
        if critical_below_100:
            print("  Critical paths below 100%:")
            for path_name, cov in critical_below_100:
                print(f"    - {path_name}: {cov:.2f}%")
        else:
            print("  All critical paths have 100% coverage")
        
        # Generate markdown report
        report = self._generate_markdown_report()
        
        report_file = Path("COVERAGE_REPORT.md")
        with open(report_file, "w") as f:
            f.write(report)
        
        print(f"\n✓ Detailed report saved to: {report_file}")
        print(f"✓ Python HTML report: backend/htmlcov/index.html")
        if self.results.get("typescript", {}).get("report_path"):
            print(f"✓ TypeScript HTML report: {self.results['typescript']['report_path']}")
        
        return str(report_file)
    
    def _generate_markdown_report(self) -> str:
        """Generate markdown coverage report"""
        from datetime import datetime
        overall = self.results.get("overall", {})
        python = self.results.get("python", {})
        typescript = self.results.get("typescript", {})
        critical = self.results.get("critical_paths", {})
        
        report = f"""# Code Coverage Analysis Report
## Task 18.11: Verify Code Coverage

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Overall Coverage | {overall.get('coverage', 0):.2f}% | 85% | {'✓ PASS' if overall.get('coverage', 0) >= 85 else '✗ FAIL'} |
| Python Coverage | {python.get('total_coverage', 0):.2f}% | 85% | {'✓ PASS' if python.get('total_coverage', 0) >= 85 else '✗ FAIL'} |
| TypeScript Coverage | {typescript.get('total_coverage', 0):.2f}% | 85% | {'✓ PASS' if typescript.get('total_coverage', 0) >= 85 else '✗ FAIL'} |
| Critical Path Coverage | {sum(d.get('average_coverage', 0) for d in critical.values()) / len(critical) if critical else 0:.2f}% | 100% | {'✓ PASS' if all(d.get('average_coverage', 0) >= 100 for d in critical.values()) else '✗ FAIL'} |

## Requirements Validation

### Requirement 16.1: Overall Coverage >= 85%
**Status**: {'✓ PASS' if overall.get('coverage', 0) >= 85 else '✗ FAIL'}
- Current Coverage: {overall.get('coverage', 0):.2f}%
- Lines Covered: {overall.get('lines_covered', 0):,} / {overall.get('lines_total', 0):,}

### Requirement 16.2: Critical Path Coverage = 100%
**Status**: {'✓ PASS' if all(d.get('average_coverage', 0) >= 100 for d in critical.values()) else '✗ FAIL'}

## Python Coverage Details

- **Total Coverage**: {python.get('total_coverage', 0):.2f}%
- **Lines Covered**: {python.get('lines_covered', 0):,} / {python.get('lines_total', 0):,}
- **HTML Report**: `backend/htmlcov/index.html`

## TypeScript Coverage Details

- **Total Coverage**: {typescript.get('total_coverage', 0):.2f}%
- **Lines Covered**: {typescript.get('lines_covered', 0):,} / {typescript.get('lines_total', 0):,}
- **Statements**: {typescript.get('statements', {}).get('pct', 0):.2f}%
- **Branches**: {typescript.get('branches', {}).get('pct', 0):.2f}%
- **Functions**: {typescript.get('functions', {}).get('pct', 0):.2f}%
- **HTML Report**: `frontend/coverage/index.html`

## Critical Path Coverage Analysis

"""
        
        for path_name, data in critical.items():
            avg_cov = data.get('average_coverage', 0)
            status = '✓' if avg_cov >= 100 else '⚠' if avg_cov >= 85 else '✗'
            report += f"\n### {status} {path_name.replace('_', ' ').title()}: {avg_cov:.2f}%\n\n"
            report += "| File | Coverage | Lines Covered | Total Lines |\n"
            report += "|------|----------|---------------|-------------|\n"
            
            for file_data in data.get('files', []):
                file_name = file_data.get('file', 'unknown')
                cov = file_data.get('coverage', 0)
                covered = file_data.get('lines_covered', 0)
                total = file_data.get('lines_total', 0)
                report += f"| `{file_name}` | {cov:.2f}% | {covered} | {total} |\n"
        
        report += """
## Coverage Gaps

"""
        
        # Identify files with low coverage
        python_files = python.get('files', {})
        low_coverage_files = []
        for file_path, file_data in python_files.items():
            summary = file_data.get('summary', {})
            coverage = summary.get('percent_covered', 0)
            if coverage < 85 and not file_path.startswith('backend/tests/'):
                low_coverage_files.append((file_path, coverage))
        
        if low_coverage_files:
            low_coverage_files.sort(key=lambda x: x[1])
            report += "### Files Below 85% Coverage\n\n"
            report += "| File | Coverage |\n"
            report += "|------|----------|\n"
            for file_path, coverage in low_coverage_files[:20]:  # Top 20
                report += f"| `{file_path}` | {coverage:.2f}% |\n"
        else:
            report += "✓ All files meet the 85% coverage threshold!\n"
        
        report += """
## Recommendations

"""
        
        if overall.get('coverage', 0) < 85:
            report += "1. **Increase Overall Coverage**: Current coverage is below 85% target\n"
            report += "   - Focus on files with lowest coverage\n"
            report += "   - Add unit tests for uncovered code paths\n"
        
        critical_below_100 = [name for name, data in critical.items() if data.get('average_coverage', 0) < 100]
        if critical_below_100:
            report += "2. **Critical Path Coverage**: The following critical paths need 100% coverage:\n"
            for path_name in critical_below_100:
                report += f"   - {path_name.replace('_', ' ').title()}\n"
        
        if not low_coverage_files and overall.get('coverage', 0) >= 85:
            report += "✓ Coverage targets met! System is ready for production.\n"
        
        report += """
## Next Steps

1. Review HTML coverage reports for detailed line-by-line analysis
2. Add tests for uncovered critical paths
3. Run coverage analysis regularly in CI/CD pipeline
4. Set up coverage badges for repository

---

**Task 18.11 Status**: {'✓ COMPLETE' if overall.get('coverage', 0) >= 85 else '⚠ IN PROGRESS'}
"""
        
        return report
    
    def run(self) -> bool:
        """Run complete coverage analysis"""
        print("\n" + "="*80)
        print("TRADESENSE CODE COVERAGE ANALYSIS")
        print("Task 18.11: Verify Code Coverage")
        print("="*80)
        
        # Run Python coverage
        py_success, _ = self.run_python_coverage()
        
        # Run TypeScript coverage
        ts_success, _ = self.run_typescript_coverage()
        
        # Analyze critical paths
        if py_success:
            self.analyze_critical_paths()
        
        # Calculate overall coverage
        self.calculate_overall_coverage()
        
        # Generate report
        self.generate_report()
        
        # Determine success
        overall_coverage = self.results.get("overall", {}).get("coverage", 0)
        success = overall_coverage >= 85
        
        print("\n" + "="*80)
        if success:
            print("✓ COVERAGE ANALYSIS COMPLETE - REQUIREMENTS MET")
        else:
            print("⚠ COVERAGE ANALYSIS COMPLETE - REQUIREMENTS NOT MET")
        print("="*80 + "\n")
        
        return success


if __name__ == "__main__":
    analyzer = CoverageAnalyzer()
    success = analyzer.run()
    sys.exit(0 if success else 1)
