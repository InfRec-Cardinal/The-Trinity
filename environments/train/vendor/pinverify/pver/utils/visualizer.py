import os
import json
import base64
from io import BytesIO
from PIL import Image

class HTMLVisualizer:
    def __init__(self):
        self.css = """
        <style>
            body { font-family: sans-serif; margin: 20px; background: #f0f2f5; }
            .container { max-width: 1000px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            h1, h2, h3 { color: #333; }
            .header { border-bottom: 2px solid #eee; padding-bottom: 10px; margin-bottom: 20px; }
            .meta-info { background: #e9ecef; padding: 10px; border-radius: 4px; margin-bottom: 20px; }
            .step-card { border: 1px solid #ddd; padding: 15px; margin-bottom: 15px; border-radius: 8px; background: #fff; }
            .step-header { font-weight: bold; margin-bottom: 10px; color: #555; display: flex; justify-content: space-between; }
            .step-content { display: flex; gap: 20px; }
            .img-box { flex: 1; max-width: 400px; }
            .img-box img { width: 100%; border-radius: 4px; border: 1px solid #ccc; display: block; }
            .path-text { font-size: 10px; color: #999; margin-top: 5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
            .info-box { flex: 1; font-family: monospace; font-size: 14px; white-space: pre-wrap; background: #f8f9fa; padding: 10px; border-radius: 4px; }
            .badge { padding: 4px 8px; border-radius: 4px; color: white; font-weight: bold; font-size: 0.9em; }
            .badge-correct { background: #28a745; }
            .badge-wrong { background: #dc3545; }
            .badge-unsure { background: #ffc107; color: #333; }
            .nav-arrow { font-weight: bold; color: #007bff; }
        </style>
        """

    def _img_to_base64(self, img_path):
        if not os.path.exists(img_path):
            print(f"[Visualizer] Image not found: {img_path}")
            return ""
        try:
            img = Image.open(img_path)
            img = img.convert("RGB")                             
            img.thumbnail((500, 500)) 
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=70)
            img_str = base64.b64encode(buffered.getvalue()).decode()
            return f"data:image/jpeg;base64,{img_str}"
        except Exception as e:
            print(f"[Visualizer] Error loading {img_path}: {e}")
            return ""

    def generate_html(self, scene_id, episode_id, results, ep_dir=None):
                                                
                                                                                
        
                             
        obj_id = results.get("object_id", "N/A")
        target_obj_id = results.get("target_object_id", obj_id)
        label = results.get("label", "N/A")
        pred = results.get("prediction", "N/A")
        is_corr = results.get("is_correct", False)
        pair_type = results.get("pair_type", "N/A")
        
                                 
        descs = results.get("query_descriptions", [])
        desc_html = ""
        if descs and any(d != "No description found" for d in descs):
             desc_html = "<ul>" + "".join([f"<li>{d}</li>" for d in descs]) + "</ul>"
        else:
             desc_html = "<p style='color:#888;'>No descriptions available.</p>"
        
                                                            
        target_descs = results.get("target_descriptions", [])
        target_html = ""
        if target_descs:
            target_html = "<ul>" + "".join([f"<li>{d}</li>" for d in target_descs]) + "</ul>"
        else:
            target_html = "<p style='color:#888;'>Same as query (positive sample)</p>"
        
                    
        color = "#2ecc71" if is_corr else "#e74c3c"
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', sans-serif; background-color: #f4f6f8; margin: 20px; }}
                .container {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); max-width: 1400px; margin: 0 auto; }}
                .header {{ border-bottom: 2px solid #eee; padding-bottom: 10px; margin-bottom: 20px; }}
                .meta-tags span {{ background: #eee; padding: 4px 8px; border-radius: 4px; font-size: 0.9em; margin-right: 10px; }}
                
                .step-card {{ background: #fff; border: 1px solid #ddd; border-radius: 8px; margin-bottom: 20px; overflow: hidden; }}
                .step-header {{ background: #f8f9fa; padding: 10px 15px; border-bottom: 1px solid #ddd; display: flex; justify-content: space-between; align-items: center; }}
                
                .step-body {{ display: flex; flex-wrap: wrap; gap: 20px; padding: 15px; align-items: flex-start; }}
                
                /* Column 1: Main View */
                .col-main {{ flex: 2; min-width: 300px; max-width: 500px; }}
                .col-main img {{ width: 100%; border-radius: 4px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
                .path-text {{ font-size: 0.8em; color: #7f8c8d; margin-top: 5px; word-break: break-all; }}
                
                /* Column 2: Model Input & Config */
                .col-mid {{ flex: 1; min-width: 200px; display: flex; flex-direction: column; gap: 15px; }}
                .crop-box img {{ width: 100%; border: 2px solid #e74c3c; border-radius: 4px; }}
                .info-panel {{ background: #f8f9fa; padding: 10px; border-radius: 4px; font-size: 0.9em; }}
                .info-label {{ font-weight: bold; color: #2c3e50; font-size: 0.85em; text-transform: uppercase; }}
                .info-val {{ margin-bottom: 5px; color: #34495e; }}

                /* Column 3: State & Prompts */
                .col-right {{ flex: 1; min-width: 250px; background: #fafafa; padding: 10px; border-radius: 4px; border-left: 3px solid #3498db; }}
                .tracker-state {{ white-space: pre-wrap; font-family: monospace; font-size: 0.85em; color: #2c3e50; }}
                
                /* Collapsible Prompts */
                details {{ margin-top: 10px; border-top: 1px solid #ddd; padding-top: 10px; }}
                summary {{ cursor: pointer; color: #2980b9; font-weight: bold; outline: none; }}
                .prompt-list ul {{ padding-left: 20px; margin: 5px 0; font-size: 0.9em; color: #555; }}
                
                .decision {{ font-size: 1.1em; font-weight: bold; }}
                .nav-arrow {{ color: #e67e22; font-weight: bold; }}
                
                /* Attribute Table */
                .attr-table {{ width: 100%; border-collapse: collapse; font-size: 0.85em; margin-top: 8px; }}
                .attr-table th, .attr-table td {{ border: 1px solid #ddd; padding: 6px 8px; text-align: left; }}
                .attr-table th {{ background: #f0f0f0; font-weight: bold; }}
                .attr-table tr:nth-child(even) {{ background: #fafafa; }}
                
                /* Vote Status */
                .vote-status {{ margin-top: 10px; padding: 5px 8px; background: #e8f4f8; border-radius: 4px; font-size: 0.85em; font-weight: bold; color: #2c3e50; }}
                
                /* Dialogue Sections */
                .dialogue-section {{ margin-top: 10px; border: 1px solid #ddd; border-radius: 4px; }}
                .dialogue-section summary {{ padding: 8px; background: #f8f9fa; cursor: pointer; font-size: 0.9em; }}
                .dialogue-section summary:hover {{ background: #e9ecef; }}
                .prompt-box, .response-box {{ padding: 8px; font-size: 0.8em; }}
                .prompt-box {{ background: #fff3cd; border-bottom: 1px solid #ddd; }}
                .response-box {{ background: #d4edda; }}
                .prompt-box pre, .response-box pre {{ white-space: pre-wrap; word-wrap: break-word; margin: 5px 0; font-size: 0.85em; max-height: 150px; overflow-y: auto; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Episode Analysis: <span style="color: {color}">{pred} (GT: {label})</span></h1>
                    <div class="meta-tags">
                        <span>Scene: {scene_id}</span>
                        <span>Episode: {episode_id}</span>
                        <span>Query Object: {obj_id}</span>
                        <span>Target Object: {target_obj_id}</span>
                        <span>Pair Type: {pair_type}</span>
                    </div>
                    <div style="margin-top: 15px; background:#e8f5e9; padding:10px; border-radius:4px; border-left: 4px solid #4caf50;">
                        <h3 style="margin:0 0 10px 0; font-size:1em;">Query Descriptions (What We Search For)</h3>
                        {desc_html}
                    </div>
                    <div style="margin-top: 10px; background:#fff3e0; padding:10px; border-radius:4px; border-left: 4px solid #ff9800;">
                        <h3 style="margin:0 0 10px 0; font-size:1em;">Target in Image (Ground Truth)</h3>
                        {target_html}
                    </div>
                </div>
        """
        
        transcript = results.get("transcript", [])
        for i, step in enumerate(transcript):
            obs = step.get("observation", {})
            action = step.get("action", {})
            
                                    
            img_path = obs.get("rgb_path", "")
            img_src = ""
            if img_path.startswith("data:"):
                img_src = img_path
            else:
                                                           
                img_src = self._img_to_base64(img_path)
            
                                           
            crop_src = action.get("_debug_crop", "")
            coarse_cat = action.get("_coarse_cat", "N/A")
            coarse_src = action.get("_coarse_source", "Unknown")
            
            crop_html = ""
            if crop_src:
                                                                   
                if not crop_src.startswith("data:"):
                                                        
                    if ep_dir and not os.path.isabs(crop_src):
                        crop_src_abs = os.path.join(ep_dir, crop_src)
                    else:
                        crop_src_abs = crop_src
                    crop_src = self._img_to_base64(crop_src_abs)
                if crop_src:                                         
                    crop_html = f"""
                    <div class='crop-box'>
                        <div class='info-label'>Model Input (Crop/Ref)</div>
                        <img src='{crop_src}'>
                    </div>
                    """
            
                                               
                                                    
            info = step.get("info", {})
            tracker_state = action.get("_debug_tracker") or info.get("tracker_state", {})
            
            tracker_str = json.dumps(tracker_state, indent=2).replace('"', '').replace('{','').replace('}','').strip()
            if not tracker_str: tracker_str = "No Tracker State"
            
            nav_info = action.get('nav_rel', 'None')
                                                                    
            nav_failed = info.get("navigation_failed", False)
            if nav_failed:
                nav_info += " <span style='color:#e74c3c; font-weight:bold;'>[UNREACHABLE - stayed in place]</span>"

                                         
            per_attr = action.get('_per_attribute_results', [])
            attr_rows = ""
            for attr in per_attr:
                obs_val = attr.get('observed', 'N/A')
                acc_val = attr.get('accumulated_status', '-')
                
                status_color = "#27ae60" if obs_val in ('Matched', 'Yes') else ("#e74c3c" if obs_val in ('Contradictory', 'No') else "#f39c12")
                acc_color = "#27ae60" if acc_val in ('Matched', 'Yes') else ("#e74c3c" if acc_val in ('Contradictory', 'No') else "#999")
                
                attr_rows += f"""
                <tr>
                    <td>{attr['name']}</td>
                    <td>{attr['expected']}</td>
                    <td style='color:{status_color};font-weight:bold;'>{obs_val}</td>
                    <td style='color:{acc_color};font-size:0.9em;'>{acc_val}</td>
                </tr>
                """
            
            attr_table_html = ""
            if attr_rows:
                attr_table_html = f"""
                <table class='attr-table'>
                    <thead><tr><th>Attribute</th><th>Expected</th><th>Step Result</th><th>Tracker</th></tr></thead>
                    <tbody>{attr_rows}</tbody>
                </table>
                """
            
                         
            votes = action.get('_votes', {})
            vote_html = f"<div class='vote-status'>Votes: Yes={votes.get('yes',0)}, No={votes.get('no',0)}</div>" if votes else ""
            
                                         
                                                                                  
            step_dlgs = action.get('_step_dialogues', [])
            extract_dlg = action.get('_extraction_dialogue', {})
            coarse_dlg = action.get('_coarse_dialogue', {})
            
            dialogue_html = ""
            
            is_trained_e2e = step_dlgs and step_dlgs[0].get('type') == 'trained_e2e'

            if step_dlgs and is_trained_e2e:
                                                                 
                dlg = step_dlgs[0]
                p_text = str(dlg.get('prompt', '')).replace('<', '&lt;').replace('>', '&gt;')
                r_text = str(dlg.get('response', '')).replace('<', '&lt;').replace('>', '&gt;')
                p_verify = dlg.get('parsed_verification', 'N/A')
                p_action = dlg.get('parsed_action', 'N/A')
                p_nav = dlg.get('parsed_navigation', [])

                verify_color = "#27ae60" if p_verify == "Yes" else ("#e74c3c" if p_verify == "No" else "#f39c12")
                action_color = "#e74c3c" if p_action.upper().startswith("STOP") else "#2980b9"
                nav_list = ", ".join(p_nav) if p_nav else "none"

                dialogue_html += f"""
                <details class='dialogue-section' open>
                    <summary style='color:#6c3483; font-weight:bold;'>Trained E2E Model Output</summary>
                    <div style="padding:10px;">
                        <div style="display:flex; gap:10px; margin-bottom:10px; flex-wrap:wrap;">
                            <div style="padding:6px 12px; border-radius:4px; background:#f0f0f0;">
                                Verification: <span style="color:{verify_color}; font-weight:bold;">{p_verify}</span>
                            </div>
                            <div style="padding:6px 12px; border-radius:4px; background:#f0f0f0;">
                                Action: <span style="color:{action_color}; font-weight:bold;">{p_action}</span>
                            </div>
                            <div style="padding:6px 12px; border-radius:4px; background:#f0f0f0;">
                                Navigable: <span style="font-weight:bold;">{nav_list}</span>
                            </div>
                        </div>
                        <div class='prompt-box'><strong>Prompt:</strong><pre>{p_text}</pre></div>
                        <div class='response-box'><strong>Model Response:</strong><pre>{r_text}</pre></div>
                    </div>
                </details>
                """

            elif step_dlgs:
                                                                             
                prompts_html = ""
                for j, dlg in enumerate(step_dlgs, 1):
                    attr_name = dlg.get('attr', dlg.get('description', f'Item {j}'))
                    p_text = str(dlg.get('prompt', '')).replace('<', '&lt;').replace('>', '&gt;')
                    r_text = str(dlg.get('response', '')).replace('<', '&lt;').replace('>', '&gt;')
                    parsed = dlg.get('parsed_state', dlg.get('state', 'N/A'))
                    reason = dlg.get('reason', '')

                                    
                    reason_html = ""
                    if reason:
                        reason_html = f"<div style='background:#fff3cd; padding:5px; border-radius:3px; margin-top:5px; font-size:0.9em;'><strong>Reason:</strong> {reason}</div>"

                    prompts_html += f"""
                    <div style="margin-bottom:15px; border-bottom:1px dashed #ccc; padding-bottom:10px;">
                        <div style="font-weight:bold; color:#555; margin-bottom:5px;">Target: {attr_name} ({parsed})</div>
                        <div class='prompt-box'><strong>Q:</strong><pre>{p_text}</pre></div>
                        <div class='response-box'><strong>A:</strong><pre>{r_text}</pre></div>
                        {reason_html}
                    </div>
                    """

                dialogue_html += f"""
                <details class='dialogue-section' open>
                    <summary>Verification Details ({len(step_dlgs)} items)</summary>
                    <div style="padding:10px;">
                        {prompts_html}
                    </div>
                </details>
                """
            
            if extract_dlg and extract_dlg.get('prompt'):
                e_prompt = extract_dlg.get('prompt', '').replace('<', '&lt;').replace('>', '&gt;')
                e_response = extract_dlg.get('response', '').replace('<', '&lt;').replace('>', '&gt;')
                dialogue_html += f"""
                <details class='dialogue-section'>
                    <summary>Extraction Prompt</summary>
                    <div class='prompt-box'><strong>Prompt:</strong><pre>{e_prompt}</pre></div>
                    <div class='response-box'><strong>Response:</strong><pre>{e_response}</pre></div>
                </details>
                """
            
            if coarse_dlg and coarse_dlg.get('prompt'):
                c_prompt = coarse_dlg.get('prompt', '').replace('<', '&lt;').replace('>', '&gt;')
                c_response = coarse_dlg.get('response', '')
                dialogue_html += f"""
                <details class='dialogue-section'>
                    <summary>Coarse Category Prompt</summary>
                    <div class='prompt-box'><strong>Prompt:</strong><pre>{c_prompt}</pre></div>
                    <div class='response-box'><strong>Response:</strong> {c_response}</div>
                </details>
                """
            
                                                          
            merge_dlg = action.get('_merge_dialogue', {})
            if merge_dlg and merge_dlg.get('prompt'):
                m_prompt = merge_dlg.get('prompt', '').replace('<', '&lt;').replace('>', '&gt;')
                m_response = merge_dlg.get('response', '').replace('<', '&lt;').replace('>', '&gt;')
                m_result = merge_dlg.get('merged_result', '')
                dialogue_html += f"""
                <details class='dialogue-section' open>
                    <summary style='color:#8e44ad; font-weight:bold;'>Description Merge Prompt</summary>
                    <div class='prompt-box'><strong>Prompt:</strong><pre>{m_prompt}</pre></div>
                    <div class='response-box'><strong>Raw Response:</strong><pre>{m_response}</pre></div>
                    <div style='background:#e8daef; padding:8px; border-radius:4px; margin-top:5px;'>
                        <strong>Merged Description:</strong> {m_result}
                    </div>
                </details>
                """

                                               
            cooccur_debug = action.get('_cooccur_debug', {})
            if cooccur_debug and cooccur_debug.get('applied_inferences'):
                inferences = cooccur_debug.get('applied_inferences', [])
                inf_html = ""
                for inf in inferences:
                    attr = inf.get('attribute', 'N/A')
                    state = inf.get('inferred_state', 'N/A')
                    conf = inf.get('confidence', 0)
                    weight = inf.get('effective_weight', 0)
                    reason = inf.get('reason', '')

                    state_color = "#28a745" if state == "Matched" else "#dc3545"
                    inf_html += f"""
                    <div style="margin-bottom:8px; padding:8px; background:#f0f8ff; border-left:3px solid #17a2b8; border-radius:4px;">
                        <div><strong>{attr}</strong>: <span style="color:{state_color}; font-weight:bold;">{state}</span></div>
                        <div style="font-size:0.85em; color:#666;">Confidence: {conf:.2f}, Weight: {weight:.3f}</div>
                        <div style="font-size:0.85em; color:#555; font-style:italic;">Reason: {reason}</div>
                    </div>
                    """

                dialogue_html += f"""
                <details class='dialogue-section' open>
                    <summary style='color:#17a2b8; font-weight:bold;'>Co-occurrence Inference ({len(inferences)} inferred)</summary>
                    <div style="padding:10px;">
                        <div style="font-size:0.85em; color:#666; margin-bottom:10px;">
                            Based on {cooccur_debug.get('verified_count', 0)} verified attributes,
                            inferred {cooccur_debug.get('unverified_count', 0)} unverified attributes using LLM world knowledge.
                        </div>
                        {inf_html}
                    </div>
                </details>
                """

                       
            nbv_debug = action.get('_nbv_debug', {})
            nbv_html = ""
            if nbv_debug:
                nbv_mode = nbv_debug.get('mode', '')

                                            
                if nbv_debug.get("prompt"):
                    n_prompt = nbv_debug.get('prompt', '').replace('<', '&lt;').replace('>', '&gt;')
                    n_res = nbv_debug.get('response', '').replace('<', '&lt;').replace('>', '&gt;')
                                                               
                    secviz_src = nbv_debug.get('_secviz_image', '')
                    secviz_html = ""
                    secviz_err = nbv_debug.get('_secviz_error', '')
                    if secviz_src:
                        secviz_html = f"""
                        <div style='margin-top:8px;'>
                            <div style='font-size:0.8em; color:#e67e22; font-weight:bold; margin-bottom:4px;'>Sector Overlay (sent to LLM)</div>
                            <img src='{secviz_src}' style='max-width:100%; border:2px solid #e67e22; border-radius:4px;'>
                        </div>
                        """
                    elif secviz_err:
                        secviz_html = f"""
                        <div style='margin-top:8px; padding:4px 8px; background:#4a1010; border-radius:4px;'>
                            <span style='font-size:0.8em; color:#ff6b6b;'>Sector viz error: {secviz_err}</span>
                        </div>
                        """
                    nbv_html = f"""
                    <details style='margin-top:5px; border-top:1px dashed #ccc;' open>
                        <summary style='font-size:0.8em; color:#e67e22;'>NBV Reasoning (LLM)</summary>
                        {secviz_html}
                        <div class='prompt-box'><strong>Prompt:</strong><pre>{n_prompt}</pre></div>
                        <div class='response-box'><strong>Response:</strong><pre>{n_res}</pre></div>
                    </details>
                    """
                                                                   
                elif nbv_mode == 'trained_e2e':
                    model_nav = nbv_debug.get('model_nav_output', [])
                    model_action = nbv_debug.get('model_action', 'N/A')
                    nav_list = ", ".join(model_nav) if model_nav else "none"
                    action_color = "#e74c3c" if model_action.upper().startswith("STOP") else "#2980b9"
                    nbv_html = f"""
                    <div style='margin-top:5px; border-top:1px dashed #ccc; padding-top:5px;'>
                        <div style='font-size:0.8em; color:#6c3483; font-weight:bold;'>Navigation (Trained E2E)</div>
                        <div style='padding:5px; font-size:0.85em;'>
                            <div>Navigable sectors: <strong>{nav_list}</strong></div>
                            <div>Action: <span style='color:{action_color}; font-weight:bold;'>{model_action}</span></div>
                        </div>
                    </div>
                    """
                                           
                elif nbv_mode == 'farthest_point':
                    target = nbv_debug.get('target', 'N/A')
                    rel_dir = nbv_debug.get('relative_direction', 'N/A')
                    method = nbv_debug.get('method', 'N/A')
                    best_diff = nbv_debug.get('best_min_angle_diff_deg', None)

                    fps_summary = f"Target: Sector {target} ({rel_dir}), Method: {method}"
                    if best_diff is not None:
                        fps_summary += f", Max Min Angle: {best_diff:.1f}°"

                                                  
                    scores_html = ""
                    if 'candidate_scores' in nbv_debug:
                        scores_html = "<table style='font-size:0.8em; border-collapse:collapse; margin-top:5px;'>"
                        scores_html += "<tr style='background:#f5f5f5;'><th style='padding:3px;'>Sector</th><th style='padding:3px;'>Angle</th><th style='padding:3px;'>Min Diff</th></tr>"
                        for sector_id, scores in sorted(nbv_debug['candidate_scores'].items()):
                            sec_angle = scores.get('sector_angle_deg', 'N/A')
                            min_diff = scores.get('min_angle_diff_deg', 0)
                            row_style = "background:#e8f5e9;" if sector_id == target else ""
                            scores_html += f"<tr style='{row_style}'><td style='padding:3px;'>{sector_id}</td><td style='padding:3px;'>{sec_angle:.1f}°</td><td style='padding:3px;'>{min_diff:.1f}°</td></tr>"
                        scores_html += "</table>"

                    nbv_html = f"""
                    <details style='margin-top:5px; border-top:1px dashed #ccc;'>
                        <summary style='font-size:0.8em; color:#27ae60;'>NBV (FPS - Geometric)</summary>
                        <div style='padding:5px; font-size:0.85em;'>
                            <strong>Summary:</strong> {fps_summary}
                            {scores_html}
                        </div>
                    </details>
                    """
            
                              
            fusion_debug = action.get('_fusion_debug', {})
            fusion_html = ""
            if fusion_debug and fusion_debug.get("mode") == "trained_e2e":
                f_verify = fusion_debug.get('verification', 'N/A')
                f_action = fusion_debug.get('action', 'N/A')
                verify_color = "#27ae60" if f_verify == "Yes" else ("#e74c3c" if f_verify == "No" else "#f39c12")
                action_color = "#e74c3c" if f_action.upper().startswith("STOP") else "#2980b9"
                fusion_html = f"""
                <div style='margin-top:5px; border-top:1px dashed #ccc; padding-top:8px;'>
                    <div style='font-size:0.9em; color:#6c3483; font-weight:bold;'>Decision (Trained E2E)</div>
                    <div style='padding:5px; font-size:0.9em; display:flex; gap:15px;'>
                        <span>Verification: <span style='color:{verify_color}; font-weight:bold;'>{f_verify}</span></span>
                        <span>Action: <span style='color:{action_color}; font-weight:bold;'>{f_action}</span></span>
                    </div>
                </div>
                """
            elif fusion_debug and fusion_debug.get("mode") == "llm_based_fusion":
                f_prompt = fusion_debug.get('prompt', '').replace('<', '&lt;').replace('>', '&gt;')
                f_res = fusion_debug.get('response', '').replace('<', '&lt;').replace('>', '&gt;')
                f_decision = fusion_debug.get('parsed_decision', 'N/A')
                f_confidence = fusion_debug.get('confidence', 'N/A')
                fusion_html = f"""
                <details style='margin-top:5px; border-top:1px dashed #ccc;' open>
                    <summary style='font-size:0.9em; color:#9b59b6; font-weight:bold;'>LLM Fusion ({f_decision}, {f_confidence})</summary>
                    <div class='prompt-box'><strong>Evidence Prompt:</strong><pre>{f_prompt}</pre></div>
                    <div class='response-box'><strong>LLM Response:</strong><pre>{f_res}</pre></div>
                </details>
                """

                                 
            clip_scores = action.get('_clip_scores', {})
            clip_html = ""
            if clip_scores:
                descs = clip_scores.get('descriptions', self.query_descs if hasattr(self, 'query_descs') else [])
                threshold = clip_scores.get('threshold', 0.25)

                if 'per_view' in clip_scores:
                                                  
                    per_view = clip_scores['per_view']
                    agg = clip_scores.get('aggregated', 0)
                    method = clip_scores.get('method', 'max')

                                      
                    views_html = ""
                    for v_sector, v_max, _v_scores in per_view:
                        sector_name = self.SECTORS[v_sector] if hasattr(self, 'SECTORS') and v_sector < 6 else str(v_sector)
                        views_html += f"<div style='margin-bottom:4px;'><strong>{sector_name}</strong>: score={v_max:.4f}</div>"

                                                           
                    last_scores = per_view[-1][2] if per_view else []
                    bars_html = ""
                    for j, score in enumerate(last_scores):
                        desc_text = descs[j][:60] + "..." if j < len(descs) and len(descs[j]) > 60 else (descs[j] if j < len(descs) else f"desc{j+1}")
                        bar_width = max(0, min(100, score * 300))                        
                        bar_color = "#27ae60" if score > threshold else "#e74c3c"
                        bars_html += f"""
                        <div style="margin-bottom:6px;">
                            <div style="font-size:0.8em; color:#555; margin-bottom:2px;">"{desc_text}"</div>
                            <div style="display:flex; align-items:center; gap:8px;">
                                <div style="width:60%; background:#eee; border-radius:3px; height:14px;">
                                    <div style="width:{bar_width}%; background:{bar_color}; border-radius:3px; height:100%;"></div>
                                </div>
                                <span style="font-weight:bold; color:{bar_color}; font-size:0.85em;">{score:.4f}</span>
                            </div>
                        </div>
                        """

                    agg_color = "#27ae60" if agg > threshold else "#e74c3c"
                    clip_html = f"""
                    <div style="margin-top:12px; padding:10px; background:#fff8e1; border-radius:6px; border-left:4px solid #ff9800;">
                        <div style="font-weight:bold; color:#e65100; margin-bottom:8px;">CLIP Similarity Scores</div>
                        {bars_html}
                        <div style="margin-top:8px; font-size:0.85em; color:#666;">Views: {len(per_view)}</div>
                        {views_html}
                        <div style="margin-top:8px; padding:6px; background:white; border-radius:4px; text-align:center;">
                            <strong>Aggregated ({method}):</strong>
                            <span style="color:{agg_color}; font-weight:bold; font-size:1.1em;">{agg:.4f}</span>
                            <span style="color:#888;"> | threshold: {threshold}</span>
                        </div>
                    </div>
                    """
                elif 'current_view' in clip_scores:
                                                                 
                    cur_score = clip_scores.get('current_view', 0)
                    all_scores = clip_scores.get('all_scores', [])

                    bars_html = ""
                    for j, score in enumerate(all_scores):
                        desc_text = descs[j][:60] + "..." if j < len(descs) and len(descs[j]) > 60 else (descs[j] if j < len(descs) else f"desc{j+1}")
                        bar_width = max(0, min(100, score * 300))
                        bar_color = "#27ae60" if score > threshold else "#e74c3c"
                        bars_html += f"""
                        <div style="margin-bottom:6px;">
                            <div style="font-size:0.8em; color:#555; margin-bottom:2px;">"{desc_text}"</div>
                            <div style="display:flex; align-items:center; gap:8px;">
                                <div style="width:60%; background:#eee; border-radius:3px; height:14px;">
                                    <div style="width:{bar_width}%; background:{bar_color}; border-radius:3px; height:100%;"></div>
                                </div>
                                <span style="font-weight:bold; color:{bar_color}; font-size:0.85em;">{score:.4f}</span>
                            </div>
                        </div>
                        """

                    cur_color = "#27ae60" if cur_score > threshold else "#e74c3c"
                    clip_html = f"""
                    <div style="margin-top:12px; padding:10px; background:#fff8e1; border-radius:6px; border-left:4px solid #ff9800;">
                        <div style="font-weight:bold; color:#e65100; margin-bottom:8px;">CLIP Similarity (this view)</div>
                        {bars_html}
                        <div style="margin-top:6px; padding:4px; text-align:center;">
                            <strong>Max:</strong> <span style="color:{cur_color}; font-weight:bold;">{cur_score:.4f}</span>
                            <span style="color:#888;"> | threshold: {threshold}</span>
                        </div>
                    </div>
                    """

            html += f"""
            <div class='step-card'>
                <div class='step-header'>
                    <span>Step {i+1}</span>
                    <span class='decision'>Decision: {action.get('decision', 'N/A')}</span>
                </div>
                <div class='step-body'>
                    <!-- Col 1 -->
                    <div class='col-main'>
                        <img src='{img_src}' alt='Main View'>
                        <div class='path-text'>{img_path}</div>
                    </div>

                    <!-- Col 2 -->
                    <div class='col-mid'>
                        <div class='info-panel'>
                            <div class='info-label'>Coarse Category</div>
                            <div class='info-val'>{coarse_cat} <span style='font-size:0.8em; color:#888'>({coarse_src})</span></div>
                            <div class='info-label'>Navigation</div>
                            <div class='info-val nav-arrow'>{nav_info}</div>
                            <!-- NBV Debug -->
                            {nbv_html}
                        </div>
                        {crop_html}
                    </div>

                    <!-- Col 3 -->
                    <div class='col-right'>
                        <div class='info-label'>Attribute Verification</div>
                        {attr_table_html}
                        {vote_html}
                        {dialogue_html}
                        {clip_html}
                        {fusion_html}
                    </div>
                </div>
            </div>
            """
            
        html += """
            </div>
        </body>
        </html>
        """
        
        return html

    def save_episode(self, ep_result, output_path):
        scene_id = ep_result.get("scene_id", "Unknown")
        episode_id = ep_result.get("episode_id", "Unknown")
                                                                                
        ep_dir = os.path.dirname(output_path)
        html_content = self.generate_html(scene_id, episode_id, ep_result, ep_dir=ep_dir)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
