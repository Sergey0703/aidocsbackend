# utils/excel_export.py
# Excel export utilities for RAG search results

import pandas as pd
import streamlit as st
import io
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class RAGExcelExporter:
    """Excel exporter for RAG search results"""
    
    def __init__(self):
        self.default_sheets = ["Search Results", "Search Summary", "Quality Analysis"]
    
    def create_results_dataframe(self, search_results: Dict) -> Optional[pd.DataFrame]:
        """Create DataFrame from search results for Excel export"""
        if not search_results or not search_results.get("fusion_result") or not search_results["fusion_result"].fused_results:
            return None
        
        results = search_results["fusion_result"].fused_results
        
        # Prepare data for DataFrame
        data = []
        for i, result in enumerate(results, 1):
            data.append({
                "?": i,
                "Filename": result.filename,
                "Similarity Score": round(result.similarity_score, 4),
                "Source Method": result.source_method,
                "Content Preview": result.content[:200] + "..." if len(result.content) > 200 else result.content,
                "Full Content": result.full_content,
                "Document ID": result.document_id,
                "Chunk Index": result.chunk_index,
                # Metadata fields
                "Content Validated": result.metadata.get("content_validated", False),
                "Match Type": result.metadata.get("match_type", ""),
                "Weighted Score": round(result.metadata.get("weighted_score", 0), 4),
                "Final Score": round(result.metadata.get("final_score", 0), 4),
                "Person Detected": result.metadata.get("universal_person_detected", False),
                "Smart Threshold": result.metadata.get("smart_threshold_used", 0)
            })
        
        return pd.DataFrame(data)
    
    def create_search_summary_dataframe(self, search_results: Dict) -> Optional[pd.DataFrame]:
        """Create summary DataFrame with search metadata"""
        if not search_results:
            return None
        
        summary_data = {
            "Search Query": [search_results["original_question"]],
            "Entity Extracted": [search_results["entity_result"].entity],
            "Extraction Method": [search_results["entity_result"].method],
            "Extraction Confidence": [round(search_results["entity_result"].confidence, 4)],
            "Query Variants Generated": [len(search_results["rewrite_result"].rewrites)],
            "Rewrite Method": [search_results["rewrite_result"].method],
            "Total Candidates Found": [search_results["retrieval_result"].total_candidates],
            "Final Results Count": [search_results["fusion_result"].final_count],
            "Retrieval Methods Used": [", ".join(search_results["retrieval_result"].methods_used)],
            "Fusion Method": [search_results["fusion_result"].fusion_method],
            "Total Search Time (s)": [round(search_results["performance_metrics"]["total_time"], 3)],
            "Entity Extraction Time (s)": [round(search_results["performance_metrics"]["extraction_time"], 3)],
            "Query Rewriting Time (s)": [round(search_results["performance_metrics"]["rewrite_time"], 3)],
            "Retrieval Time (s)": [round(search_results["performance_metrics"]["retrieval_time"], 3)],
            "Fusion Time (s)": [round(search_results["performance_metrics"]["fusion_time"], 3)],
            "Answer Generation Time (s)": [round(search_results["performance_metrics"]["answer_time"], 3)],
            "Search Timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            "System Performance (q/s)": [round(1/search_results["performance_metrics"]["total_time"], 2)]
        }
        
        return pd.DataFrame(summary_data)
    
    def create_quality_analysis_dataframe(self, results_df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Create quality analysis DataFrame"""
        if results_df is None or results_df.empty:
            return None
        
        try:
            # Group by source method and analyze quality
            quality_stats = results_df.groupby("Source Method").agg({
                "Similarity Score": ["count", "mean", "std", "min", "max"],
                "Weighted Score": ["mean", "std"],
                "Final Score": ["mean", "std"]
            }).round(4)
            
            # Flatten column names
            quality_stats.columns = [
                "Document Count", "Avg Similarity", "Std Similarity", "Min Similarity", "Max Similarity",
                "Avg Weighted Score", "Std Weighted Score", "Avg Final Score", "Std Final Score"
            ]
            
            # Add percentage of total results
            total_docs = len(results_df)
            quality_stats["Percentage of Results"] = round((quality_stats["Document Count"] / total_docs) * 100, 1)
            
            # Add quality rating
            quality_stats["Quality Rating"] = quality_stats["Avg Similarity"].apply(
                lambda x: "Excellent" if x >= 0.8 else "Good" if x >= 0.6 else "Moderate" if x >= 0.4 else "Low"
            )
            
            return quality_stats.reset_index()
            
        except Exception as e:
            logger.warning(f"Error creating quality analysis: {e}")
            return None
    
    def create_performance_breakdown_dataframe(self, search_results: Dict) -> Optional[pd.DataFrame]:
        """Create performance breakdown DataFrame"""
        if not search_results or "performance_metrics" not in search_results:
            return None
        
        metrics = search_results["performance_metrics"]
        efficiency = metrics.get("pipeline_efficiency", {})
        
        performance_data = [
            {"Stage": "Entity Extraction", "Time (s)": round(metrics["extraction_time"], 3), "Percentage": f"{efficiency.get('extraction_pct', 0):.1f}%"},
            {"Stage": "Query Rewriting", "Time (s)": round(metrics["rewrite_time"], 3), "Percentage": f"{efficiency.get('rewrite_pct', 0):.1f}%"},
            {"Stage": "Multi-Retrieval", "Time (s)": round(metrics["retrieval_time"], 3), "Percentage": f"{efficiency.get('retrieval_pct', 0):.1f}%"},
            {"Stage": "Results Fusion", "Time (s)": round(metrics["fusion_time"], 3), "Percentage": f"{efficiency.get('fusion_pct', 0):.1f}%"},
            {"Stage": "Answer Generation", "Time (s)": round(metrics["answer_time"], 3), "Percentage": f"{efficiency.get('answer_pct', 0):.1f}%"},
            {"Stage": "**TOTAL**", "Time (s)": round(metrics["total_time"], 3), "Percentage": "100.0%"}
        ]
        
        return pd.DataFrame(performance_data)
    
    def to_excel_bytes(self, dataframes_dict: Dict[str, pd.DataFrame]) -> bytes:
        """Convert multiple DataFrames to Excel bytes for download"""
        buffer = io.BytesIO()
        
        try:
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                # Write each DataFrame to a separate sheet
                for sheet_name, df in dataframes_dict.items():
                    if df is not None and not df.empty:
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                        
                        # Get workbook and worksheet for formatting
                        workbook = writer.book
                        worksheet = writer.sheets[sheet_name]
                        
                        # Define formats
                        header_format = workbook.add_format({
                            'bold': True,
                            'text_wrap': True,
                            'valign': 'top',
                            'fg_color': '#D7E4BC',
                            'border': 1,
                            'font_size': 10
                        })
                        
                        number_format = workbook.add_format({'num_format': '0.0000'})
                        percentage_format = workbook.add_format({'num_format': '0.0%'})
                        
                        # Format headers
                        for col_num, value in enumerate(df.columns.values):
                            worksheet.write(0, col_num, value, header_format)
                        
                        # Auto-adjust column widths and apply number formatting
                        for column in df:
                            column_length = max(
                                df[column].astype(str).map(len).max(),  # len of largest item
                                len(str(column))  # len of column name/header
                            ) + 2  # adding a little extra space
                            
                            col_idx = df.columns.get_loc(column)
                            worksheet.set_column(col_idx, col_idx, min(column_length, 50))
                            
                            # Apply number formatting to score columns
                            if any(word in column.lower() for word in ['score', 'time', 'confidence']):
                                if 'percentage' not in column.lower():
                                    worksheet.set_column(col_idx, col_idx, None, number_format)
            
            buffer.seek(0)
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error creating Excel file: {e}")
            raise
    
    def generate_filename(self, search_results: Dict) -> str:
        """Generate default filename for export"""
        try:
            entity = search_results["entity_result"].entity.replace(" ", "_").replace("/", "_")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"rag_search_{entity}_{timestamp}.xlsx"
        except:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"rag_search_{timestamp}.xlsx"

def render_excel_export_section(search_results: Dict):
    """Render Excel export section in Streamlit interface"""
    if not search_results or not search_results.get("fusion_result") or not search_results["fusion_result"].fused_results:
        return
    
    exporter = RAGExcelExporter()
    
    st.markdown("---")
    st.header("?? Export Search Results")
    
    # Create DataFrames
    results_df = exporter.create_results_dataframe(search_results)
    summary_df = exporter.create_search_summary_dataframe(search_results)
    quality_df = exporter.create_quality_analysis_dataframe(results_df)
    performance_df = exporter.create_performance_breakdown_dataframe(search_results)
    
    if results_df is None:
        st.warning("?? No results to export")
        return
    
    # Show preview of what will be exported
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("?? Results Preview")
        st.write(f"**{len(results_df)} documents found**")
        preview_df = results_df[["?", "Filename", "Similarity Score", "Source Method"]].head(3)
        st.dataframe(preview_df, use_container_width=True)
    
    with col2:
        st.subheader("?? Search Summary")
        if summary_df is not None:
            # Display key metrics
            st.metric("?? Query", search_results["original_question"])
            st.metric("?? Entity", search_results["entity_result"].entity)
            st.metric("?? Results", search_results["fusion_result"].final_count)
            st.metric("?? Time", f"{search_results['performance_metrics']['total_time']:.2f}s")
    
    # Export options
    st.subheader("?? Export Options")
    
    export_cols = st.columns([3, 1, 1])
    
    with export_cols[0]:
        # File naming
        default_filename = exporter.generate_filename(search_results)
        filename = st.text_input("?? Export filename:", value=default_filename)
    
    with export_cols[1]:
        include_summary = st.checkbox("?? Include Summary", value=True)
        include_performance = st.checkbox("? Include Performance", value=True)
    
    with export_cols[2]:
        include_full_content = st.checkbox("?? Full Content", value=False)
        include_quality = st.checkbox("?? Quality Analysis", value=True)
    
    # Prepare DataFrames for export
    export_dataframes = {}
    
    # Results sheet (main data)
    if include_full_content:
        export_dataframes["Search Results"] = results_df
    else:
        # Exclude full content column to save space
        export_df = results_df.drop(columns=["Full Content"], errors='ignore')
        export_dataframes["Search Results"] = export_df
    
    # Optional sheets
    if include_summary and summary_df is not None:
        export_dataframes["Search Summary"] = summary_df
    
    if include_quality and quality_df is not None:
        export_dataframes["Quality Analysis"] = quality_df
    
    if include_performance and performance_df is not None:
        export_dataframes["Performance Breakdown"] = performance_df
    
    # Generate Excel file and download button
    try:
        excel_data = exporter.to_excel_bytes(export_dataframes)
        
        # Download button
        st.download_button(
            label="?? Download Excel Report",
            data=excel_data,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True
        )
        
        # Show what will be included
        sheets_info = []
        sheets_info.append(f"**?? Search Results**: {len(results_df)} documents with scores and metadata")
        
        if include_summary:
            sheets_info.append("**?? Search Summary**: Query details and performance metrics")
        if include_quality:
            sheets_info.append("**?? Quality Analysis**: Performance breakdown by source method")
        if include_performance:
            sheets_info.append("**? Performance Breakdown**: Time distribution across pipeline stages")
        if include_full_content:
            sheets_info.append("**?? Full Content**: Complete document text (?? Large file size)")
        
        st.success(f"""
        **?? Excel file will include {len(export_dataframes)} sheets:**
        
        {chr(10).join(f" {info}" for info in sheets_info)}
        """)
        
    except Exception as e:
        st.error(f"? Error generating Excel file: {e}")
        logger.error(f"Excel export error: {e}")

# Convenience function for easy import
def add_excel_export_to_results(search_results: Dict):
    """Add Excel export section to search results - convenience function"""
    render_excel_export_section(search_results)