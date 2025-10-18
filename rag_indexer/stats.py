#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Statistics and monitoring script for RAG Document Indexer
Analyzes Docling metadata and provides quality reports
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import argparse


class ConversionStats:
    """Analyzer for Docling conversion metadata"""
    
    def __init__(self, metadata_dir="./data/markdown/_metadata"):
        self.metadata_dir = Path(metadata_dir)
        self.metadata_files = []
        self.stats = {
            'total_conversions': 0,
            'by_format': defaultdict(int),
            'by_quality': defaultdict(int),
            'quality_scores': [],
            'total_original_size': 0,
            'total_markdown_size': 0,
            'problematic_files': [],
            'conversion_timeline': [],
            'average_conversion_time': 0,
        }
    
    def load_metadata(self):
        """Load all metadata JSON files"""
        if not self.metadata_dir.exists():
            print(f"Metadata directory not found: {self.metadata_dir}")
            return False
        
        self.metadata_files = list(self.metadata_dir.glob("*.json"))
        
        if not self.metadata_files:
            print(f"No metadata files found in {self.metadata_dir}")
            return False
        
        print(f"Found {len(self.metadata_files)} metadata files")
        return True
    
    def analyze(self):
        """Analyze all metadata files"""
        print("\nAnalyzing metadata...")
        
        for meta_file in self.metadata_files:
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                self._process_metadata(metadata)
                
            except Exception as e:
                print(f"Error reading {meta_file.name}: {e}")
                continue
        
        # Calculate averages
        if self.stats['quality_scores']:
            self.stats['average_quality'] = sum(self.stats['quality_scores']) / len(self.stats['quality_scores'])
        
        # Sort problematic files by quality score
        self.stats['problematic_files'].sort(key=lambda x: x['quality_score'])
    
    def _process_metadata(self, metadata):
        """Process single metadata file"""
        self.stats['total_conversions'] += 1
        
        # Format statistics
        fmt = metadata.get('original_format', 'unknown')
        self.stats['by_format'][fmt] += 1
        
        # Quality score
        quality_score = metadata.get('conversion_quality_score', 0)
        self.stats['quality_scores'].append(quality_score)
        
        # Categorize quality
        if quality_score >= 90:
            self.stats['by_quality']['excellent'] += 1
        elif quality_score >= 75:
            self.stats['by_quality']['good'] += 1
        elif quality_score >= 50:
            self.stats['by_quality']['acceptable'] += 1
        else:
            self.stats['by_quality']['poor'] += 1
        
        # Track problematic files (quality < 75)
        if quality_score < 75:
            self.stats['problematic_files'].append({
                'filename': metadata.get('original_filename', 'unknown'),
                'quality_score': quality_score,
                'format': fmt,
                'original_size': metadata.get('original_size_bytes', 0),
                'markdown_size': metadata.get('markdown_size_bytes', 0),
                'conversion_time': metadata.get('conversion_time_seconds', 0)
            })
        
        # Size statistics
        self.stats['total_original_size'] += metadata.get('original_size_bytes', 0)
        self.stats['total_markdown_size'] += metadata.get('markdown_size_bytes', 0)
        
        # Timeline
        self.stats['conversion_timeline'].append({
            'date': metadata.get('conversion_date', 'unknown'),
            'filename': metadata.get('original_filename', 'unknown'),
            'quality': quality_score
        })
        
        # Conversion time
        conv_time = metadata.get('conversion_time_seconds', 0)
        if conv_time > 0:
            current_avg = self.stats['average_conversion_time']
            count = self.stats['total_conversions']
            self.stats['average_conversion_time'] = (current_avg * (count - 1) + conv_time) / count
    
    def print_summary(self):
        """Print summary statistics"""
        print("\n" + "="*70)
        print("DOCLING CONVERSION STATISTICS")
        print("="*70)
        
        print(f"\nTotal conversions: {self.stats['total_conversions']}")
        
        # Format breakdown
        print("\nBy format:")
        for fmt, count in sorted(self.stats['by_format'].items(), key=lambda x: x[1], reverse=True):
            percentage = (count / self.stats['total_conversions']) * 100
            print(f"  {fmt.upper()}: {count} ({percentage:.1f}%)")
        
        # Quality breakdown
        print("\nBy quality:")
        for quality, count in sorted(self.stats['by_quality'].items()):
            percentage = (count / self.stats['total_conversions']) * 100
            print(f"  {quality.capitalize()}: {count} ({percentage:.1f}%)")
        
        # Average quality
        if 'average_quality' in self.stats:
            print(f"\nAverage quality score: {self.stats['average_quality']:.1f}/100")
        
        # Size comparison
        orig_size_mb = self.stats['total_original_size'] / (1024 * 1024)
        md_size_mb = self.stats['total_markdown_size'] / (1024 * 1024)
        
        print(f"\nSize comparison:")
        print(f"  Original files: {orig_size_mb:.2f} MB")
        print(f"  Markdown files: {md_size_mb:.2f} MB")
        
        if orig_size_mb > 0:
            ratio = (md_size_mb / orig_size_mb) * 100
            print(f"  Markdown is {ratio:.1f}% of original size")
        
        # Performance
        print(f"\nPerformance:")
        print(f"  Average conversion time: {self.stats['average_conversion_time']:.2f}s")
    
    def print_problematic_files(self, limit=10):
        """Print problematic files report"""
        if not self.stats['problematic_files']:
            print("\n✅ No problematic files found (all quality scores >= 75)")
            return
        
        print("\n" + "="*70)
        print(f"PROBLEMATIC FILES (quality < 75) - Top {limit}")
        print("="*70)
        
        for i, file_info in enumerate(self.stats['problematic_files'][:limit], 1):
            print(f"\n{i}. {file_info['filename']}")
            print(f"   Quality score: {file_info['quality_score']:.1f}/100")
            print(f"   Format: {file_info['format'].upper()}")
            print(f"   Original size: {file_info['original_size']/1024:.1f} KB")
            print(f"   Markdown size: {file_info['markdown_size']/1024:.1f} KB")
            print(f"   Conversion time: {file_info['conversion_time']:.2f}s")
        
        if len(self.stats['problematic_files']) > limit:
            print(f"\n... and {len(self.stats['problematic_files']) - limit} more problematic files")
    
    def print_timeline(self, limit=10):
        """Print recent conversion timeline"""
        if not self.stats['conversion_timeline']:
            return
        
        print("\n" + "="*70)
        print(f"RECENT CONVERSIONS - Last {limit}")
        print("="*70)
        
        # Sort by date (most recent first)
        sorted_timeline = sorted(
            self.stats['conversion_timeline'],
            key=lambda x: x['date'],
            reverse=True
        )
        
        for i, entry in enumerate(sorted_timeline[:limit], 1):
            date_str = entry['date'][:19] if len(entry['date']) > 19 else entry['date']
            quality_emoji = "✅" if entry['quality'] >= 75 else "⚠️"
            print(f"{i}. {date_str} - {entry['filename']} {quality_emoji} ({entry['quality']:.0f})")
    
    def export_json(self, output_file="./logs/conversion_stats.json"):
        """Export statistics to JSON"""
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert defaultdict to regular dict for JSON
            export_data = {
                'generated_at': datetime.now().isoformat(),
                'total_conversions': self.stats['total_conversions'],
                'by_format': dict(self.stats['by_format']),
                'by_quality': dict(self.stats['by_quality']),
                'average_quality': self.stats.get('average_quality', 0),
                'total_original_size_mb': self.stats['total_original_size'] / (1024 * 1024),
                'total_markdown_size_mb': self.stats['total_markdown_size'] / (1024 * 1024),
                'average_conversion_time': self.stats['average_conversion_time'],
                'problematic_files_count': len(self.stats['problematic_files']),
                'problematic_files': self.stats['problematic_files'][:20],  # Top 20
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n📊 Statistics exported to: {output_path}")
            return True
            
        except Exception as e:
            print(f"\n❌ Error exporting statistics: {e}")
            return False


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Analyze Docling conversion metadata and quality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show full statistics
  python stats.py
  
  # Show only problematic files
  python stats.py --problematic
  
  # Export to JSON
  python stats.py --export
  
  # Custom metadata directory
  python stats.py --metadata ./custom/metadata
        """
    )
    
    parser.add_argument(
        '--metadata',
        type=str,
        default='./data/markdown/_metadata',
        help='Path to metadata directory (default: ./data/markdown/_metadata)'
    )
    
    parser.add_argument(
        '--problematic',
        action='store_true',
        help='Show only problematic files (quality < 75)'
    )
    
    parser.add_argument(
        '--export',
        action='store_true',
        help='Export statistics to JSON file'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=10,
        help='Limit number of items to display (default: 10)'
    )
    
    args = parser.parse_args()
    
    # Create analyzer
    analyzer = ConversionStats(metadata_dir=args.metadata)
    
    # Load metadata
    if not analyzer.load_metadata():
        sys.exit(1)
    
    # Analyze
    analyzer.analyze()
    
    # Display results
    if args.problematic:
        analyzer.print_problematic_files(limit=args.limit)
    else:
        analyzer.print_summary()
        analyzer.print_problematic_files(limit=args.limit)
        analyzer.print_timeline(limit=args.limit)
    
    # Export if requested
    if args.export:
        analyzer.export_json()
    
    print("\n" + "="*70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)