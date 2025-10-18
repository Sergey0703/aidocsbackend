#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simplified analysis helpers module for RAG Document Indexer (Part 2: Chunking & Vectors Only)
Contains helper functions for result analysis and reporting
SIMPLIFIED: Removed OCR, PDF, document conversion statistics
"""

from datetime import datetime
from .utils import save_failed_files_details


def analyze_final_results_enhanced(config, db_manager, log_dir, processing_stats):
    """
    Simplified end-to-end analysis with comprehensive reporting
    
    Args:
        config: Configuration object
        db_manager: Database manager instance
        log_dir: Directory for log files
        processing_stats: Processing statistics from all stages
    
    Returns:
        dict: Comprehensive analysis results
    """
    print(f"\n{'='*70}")
    print("🔍 END-TO-END ANALYSIS")
    print(f"{'='*70}")
    
    # Perform comprehensive directory vs database comparison WITH blacklist
    analysis_results = db_manager.analyze_directory_vs_database(
        config.DOCUMENTS_DIR, 
        recursive=True,
        blacklist_directories=config.BLACKLIST_DIRECTORIES  # FIXED: Pass blacklist
    )
    
    # Extract results
    total_files = analysis_results['total_files_in_directory']
    files_in_db = analysis_results['files_successfully_in_db']
    missing_files = analysis_results['files_missing_from_db']
    missing_files_detailed = analysis_results['missing_files_detailed']
    success_rate = analysis_results['success_rate']
    
    print(f"\n📊 Final Processing Results:")
    print(f"   📁 Total markdown files in directory: {total_files:,}")
    print(f"   ✅ Files successfully in database: {files_in_db:,}")
    print(f"   ❌ Files missing from database: {missing_files:,}")
    print(f"   📈 End-to-end success rate: {success_rate:.1f}%")
    
    # Simplified pipeline analysis
    if processing_stats:
        print_pipeline_analysis(processing_stats)
    
    # Handle failed files analysis
    failure_analysis = analyze_failed_files(missing_files_detailed, log_dir)
    
    # Simplified results
    enhanced_analysis = {
        **analysis_results,  # Include original analysis
        'processing_stats': processing_stats,
        'pipeline_success': processing_stats.get('records_saved', 0) > 0,
        'performance_metrics': calculate_performance_metrics(processing_stats),
        'failure_analysis': failure_analysis
    }
    
    return enhanced_analysis


def print_pipeline_analysis(processing_stats):
    """
    Print simplified pipeline analysis
    
    Args:
        processing_stats: Processing statistics dictionary
    """
    print(f"\n🔄 Processing Pipeline Analysis:")
    
    # Document loading stage
    if 'documents_loaded' in processing_stats:
        print(f"   📄 Documents loaded: {processing_stats['documents_loaded']:,}")
    
    # Chunk processing stage  
    if 'chunks_created' in processing_stats:
        print(f"   🧩 Chunks created: {processing_stats['chunks_created']:,}")
    
    if 'valid_chunks' in processing_stats:
        print(f"   ✅ Valid chunks: {processing_stats['valid_chunks']:,}")
    
    # Database stage
    if 'records_saved' in processing_stats:
        print(f"   💾 Records saved to database: {processing_stats['records_saved']:,}")
    
    # Calculate pipeline loss at each stage
    total_attempted = processing_stats.get('chunks_created', 0)
    if total_attempted > 0:
        saved_records = processing_stats.get('records_saved', 0)
        pipeline_loss = total_attempted - saved_records
        loss_rate = (pipeline_loss / total_attempted * 100)
        
        print(f"\n📉 Pipeline Loss Analysis:")
        print(f"   Total chunks attempted: {total_attempted:,}")
        print(f"   Successfully saved: {saved_records:,}")
        print(f"   Lost in pipeline: {pipeline_loss:,}")
        print(f"   Pipeline loss rate: {loss_rate:.2f}%")


def analyze_failed_files(missing_files_detailed, log_dir):
    """
    Analyze failed files and save detailed information
    
    Args:
        missing_files_detailed: List of detailed failure information
        log_dir: Directory for log files
    
    Returns:
        dict: Failure analysis results
    """
    if not missing_files_detailed:
        print(f"\n🎉 PERFECT PROCESSING: All files successfully indexed!")
        return {'total_failed': 0, 'categories': {}, 'perfect_processing': True}
    
    print(f"\n📝 Saving detailed analysis...")
    log_file_path = save_failed_files_details(missing_files_detailed, log_dir)
    
    if log_file_path:
        print(f"   📋 Missing files details saved to: {log_file_path}")
    else:
        print(f"   ⚠️ Could not save missing files details")
    
    # Show categorized failure analysis
    failure_categories = categorize_failures(missing_files_detailed)
    
    if failure_categories:
        print(f"\n🔍 Failure Category Analysis:")
        for category, count in sorted(failure_categories.items(), key=lambda x: x[1], reverse=True):
            print(f"   {category}: {count} files")
    
    # Show first few missing files for quick reference
    print(f"\n❌ Sample Missing Files:")
    for i, missing_detail in enumerate(missing_files_detailed[:5], 1):
        print(f"   {i}. {missing_detail}")
    if len(missing_files_detailed) > 5:
        print(f"   ... and {len(missing_files_detailed) - 5} more (see detailed log)")
    
    return {
        'total_failed': len(missing_files_detailed),
        'categories': failure_categories,
        'log_file': log_file_path,
        'sample_failures': missing_files_detailed[:10],
        'perfect_processing': False
    }


def categorize_failures(missing_files_detailed):
    """
    Categorize failure reasons from detailed failure list
    
    Args:
        missing_files_detailed: List of detailed failure information
    
    Returns:
        dict: Dictionary of failure categories and counts
    """
    failure_categories = {}
    
    for missing_detail in missing_files_detailed:
        # Extract failure category from detail
        if " - " in missing_detail:
            category = missing_detail.split(" - ", 1)[1].split(" ")[0]
        else:
            category = "UNKNOWN"
        
        failure_categories[category] = failure_categories.get(category, 0) + 1
    
    return failure_categories


def calculate_performance_metrics(processing_stats):
    """
    Calculate simplified performance metrics
    
    Args:
        processing_stats: Processing statistics dictionary
    
    Returns:
        dict: Performance metrics
    """
    metrics = {}
    
    # Processing speed metrics
    if 'total_time' in processing_stats and 'records_saved' in processing_stats:
        total_time = processing_stats['total_time']
        records_saved = processing_stats['records_saved']
        if total_time > 0:
            metrics['overall_processing_speed'] = records_saved / total_time
    
    # Stage-wise performance
    if 'chunk_creation_time' in processing_stats:
        metrics['chunk_creation_speed'] = (
            processing_stats.get('chunks_created', 0) / 
            processing_stats['chunk_creation_time']
        ) if processing_stats['chunk_creation_time'] > 0 else 0
    
    if 'avg_speed' in processing_stats:
        metrics['embedding_speed'] = processing_stats['avg_speed']
    
    # Batch efficiency
    if 'total_batches' in processing_stats and 'avg_speed' in processing_stats:
        metrics['batch_efficiency'] = processing_stats['avg_speed'] * processing_stats['total_batches']
    
    return metrics


def create_enhanced_run_summary(start_time, end_time, stats, final_analysis, config):
    """
    Create simplified run summary with comprehensive statistics
    
    Args:
        start_time: Start timestamp
        end_time: End timestamp
        stats: Processing statistics
        final_analysis: Final analysis results
        config: Configuration object
    
    Returns:
        str: Formatted summary
    """
    duration = end_time - start_time
    
    summary = []
    summary.append("🚀 SIMPLIFIED RAG INDEXER RUN SUMMARY (PART 2: CHUNKING & VECTORS)")
    summary.append("=" * 70)
    summary.append(f"Start time: {datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')}")
    summary.append(f"End time: {datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')}")
    summary.append(f"Duration: {duration/60:.1f} minutes ({duration:.1f} seconds)")
    summary.append("")
    
    # Configuration summary
    summary.extend(create_config_summary(config))
    
    # Main statistics
    summary.extend(create_stats_summary(stats))
    
    # Processing stages
    if stats.get('processing_stages'):
        summary.append("")
        summary.append("🔄 PROCESSING STAGES COMPLETED:")
        for i, stage in enumerate(stats['processing_stages'], 1):
            summary.append(f"   {i}. {stage.replace('_', ' ').title()}")
    
    # Final analysis summary
    if final_analysis:
        summary.extend(create_final_analysis_summary(final_analysis))
    
    # Failed files summary
    summary.extend(create_failed_files_summary(final_analysis))
    
    summary.append("")
    summary.append("=" * 70)
    
    return "\n".join(summary)


def create_config_summary(config):
    """Create simplified configuration summary section"""
    summary = []
    summary.append("🔧 CONFIGURATION:")
    summary.append(f"   Input directory: {config.DOCUMENTS_DIR} (markdown files)")
    summary.append(f"   Embedding model: {config.EMBED_MODEL} ({config.EMBED_DIM}D)")
    summary.append(f"   Chunk size: {config.CHUNK_SIZE} (overlap: {config.CHUNK_OVERLAP})")
    summary.append(f"   Processing batch size: {config.PROCESSING_BATCH_SIZE}")
    summary.append(f"   Gemini API rate limit: {config.GEMINI_REQUEST_RATE_LIMIT} requests/sec")
    summary.append(f"   Blacklisted directories: {', '.join(config.BLACKLIST_DIRECTORIES)}")
    summary.append("")
    return summary


def create_stats_summary(stats):
    """Create main statistics summary section"""
    summary = []
    summary.append("📊 PROCESSING STATISTICS:")
    
    # Core statistics
    key_stats = [
        ('documents_loaded', 'Documents loaded'),
        ('chunks_created', 'Chunks created'),
        ('valid_chunks', 'Valid chunks'),
        ('records_saved', 'Records saved'),
        ('total_batches', 'Total batches'),
        ('failed_batches', 'Failed batches'),
        ('avg_speed', 'Average speed (chunks/sec)'),
    ]
    
    for key, label in key_stats:
        if key in stats:
            value = stats[key]
            if isinstance(value, float):
                summary.append(f"   {label}: {value:.2f}")
            elif isinstance(value, int):
                summary.append(f"   {label}: {value:,}")
    
    # Quality analysis
    if 'quality_analysis_results' in stats:
        quality_results = stats['quality_analysis_results']
        summary.append("")
        summary.append("🎯 QUALITY METRICS:")
        summary.append(f"   Filter success rate: {quality_results.get('filter_success_rate', 0):.1f}%")
        summary.append(f"   Invalid chunks filtered: {quality_results.get('invalid_chunks', 0):,}")
        summary.append(f"   Average content length: {quality_results.get('avg_content_length', 0):.0f} chars")
    
    summary.append("")
    return summary


def create_final_analysis_summary(final_analysis):
    """Create final analysis summary section"""
    summary = []
    summary.append("🔍 END-TO-END ANALYSIS:")
    summary.append(f"   Total files in directory: {final_analysis['total_files_in_directory']:,}")
    summary.append(f"   Files successfully in database: {final_analysis['files_successfully_in_db']:,}")
    summary.append(f"   Files missing from database: {final_analysis['files_missing_from_db']:,}")
    summary.append(f"   End-to-end success rate: {final_analysis['success_rate']:.1f}%")
    
    # Performance metrics
    if 'performance_metrics' in final_analysis:
        metrics = final_analysis['performance_metrics']
        summary.append("")
        summary.append("⚡ PERFORMANCE METRICS:")
        for metric, value in metrics.items():
            summary.append(f"   {metric.replace('_', ' ').title()}: {value:.2f} items/sec")
    
    summary.append("")
    return summary


def create_failed_files_summary(final_analysis):
    """Create failed files summary section"""
    summary = []
    summary.append("❌ FAILED FILES SUMMARY:")
    summary.append("-" * 40)
    
    missing_files_detailed = final_analysis.get('missing_files_detailed', []) if final_analysis else []
    
    if not missing_files_detailed:
        summary.append("✅ No failed files - perfect processing!")
    else:
        summary.append(f"❌ Total failed files: {len(missing_files_detailed)}")
        summary.append(f"📋 Details saved to: /logs/failed_files_details.log")
        
        # Show first 5 for quick reference
        if len(missing_files_detailed) <= 5:
            summary.append("")
            summary.append("All failed files:")
            for i, failed_file in enumerate(missing_files_detailed, 1):
                summary.append(f"  {i}. {failed_file}")
        else:
            summary.append("")
            summary.append("First 5 failed files:")
            for i, failed_file in enumerate(missing_files_detailed[:5], 1):
                summary.append(f"  {i}. {failed_file}")
            summary.append(f"  ... and {len(missing_files_detailed) - 5} more (see detailed log)")
    
    return summary


def create_enhanced_status_report(status_reporter, stats, final_analysis, batch_results, deletion_info, start_time, end_time):
    """
    Create simplified status report with key metrics
    
    Args:
        status_reporter: Status reporter instance
        stats: Processing statistics
        final_analysis: Final analysis results
        batch_results: Batch processing results
        deletion_info: Deletion information
        start_time: Processing start time
        end_time: Processing end time
    """
    # Final statistics
    status_reporter.add_section("📊 Final Statistics", {
        "Total processing time": f"{end_time - start_time:.2f}s ({(end_time - start_time)/60:.1f}m)",
        "Documents loaded": f"{stats['documents_loaded']:,}",
        "Chunks created": f"{stats['chunks_created']:,}",
        "Valid chunks": f"{stats['valid_chunks']:,}",
        "Records saved": f"{stats['records_saved']:,}",
        "Processing speed": f"{batch_results['avg_speed']:.2f} chunks/sec",
        "Overall success rate": f"{batch_results['success_rate']:.1f}%"
    })
    
    # End-to-end analysis
    if final_analysis:
        status_reporter.add_section("🔍 End-to-End File Analysis", {
            "Total files in directory": f"{final_analysis['total_files_in_directory']:,}",
            "Files successfully in database": f"{final_analysis['files_successfully_in_db']:,}",
            "Files missing from database": f"{final_analysis['files_missing_from_db']:,}",
            "End-to-end success rate": f"{final_analysis['success_rate']:.1f}%",
            "Missing files details": f"Saved to logs/failed_files_details.log" if final_analysis.get('missing_files_detailed') else "No missing files"
        })
    
    # Data loss analysis
    total_attempted = stats.get('chunks_created', 0)
    total_saved = stats.get('records_saved', 0)
    total_lost = total_attempted - total_saved
    loss_rate = (total_lost / total_attempted * 100) if total_attempted > 0 else 0
    
    status_reporter.add_section("📉 Data Loss Analysis", {
        "Total chunks attempted": f"{total_attempted:,}",
        "Chunks successfully saved": f"{total_saved:,}",
        "Chunks lost in pipeline": f"{total_lost:,}",
        "Pipeline loss rate": f"{loss_rate:.2f}%",
        "Main loss causes": f"See logs/invalid_chunks_report.log for details"
    })
    
    # Quality metrics
    status_reporter.add_section("🎯 Quality Metrics", {
        "Processing pipeline errors": final_analysis.get('files_missing_from_db', 0) if final_analysis else 0,
        "Failed chunks": batch_results['total_failed_chunks'],
        "Failed batches": batch_results['failed_batches'],
        "Embedding errors": batch_results['total_embedding_errors'],
        "Invalid chunks filtered": stats.get('quality_analysis_results', {}).get('invalid_chunks', 0)
    })
    
    # Performance analysis
    performance_data = {
        "Average processing speed": f"{batch_results['avg_speed']:.2f} chunks/sec",
        "Total processing time": f"{batch_results['total_time']:.1f}s"
    }
    
    if final_analysis and 'performance_metrics' in final_analysis:
        metrics = final_analysis['performance_metrics']
        for metric, value in metrics.items():
            performance_data[metric.replace('_', ' ').title()] = f"{value:.2f} items/sec"
    
    status_reporter.add_section("⚡ Performance Analysis", performance_data)
    
    # Gemini API statistics
    if 'gemini_api_calls' in stats:
        status_reporter.add_section("🚀 Gemini API Statistics", {
            "API calls made": f"{stats.get('gemini_api_calls', 0):,}",
            "Rate limit delays": f"{stats.get('rate_limit_delays', 0):,}",
            "Retry attempts used": f"{stats.get('retry_attempts_used', 0):,}"
        })