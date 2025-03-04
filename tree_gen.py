import json
import graphviz
import os
import math
from collections import defaultdict

def load_questions():
    with open("questions.json", "r") as f:
        return json.load(f)

def define_disorders():
    return {
        "296.2x": "Major Depressive Disorder",
        "296.4x": "Bipolar Disorder",
        "300.02": "Generalized Anxiety Disorder",
        "314.0x": "ADHD",
        "295.90": "Schizophrenia",
        "300.3": "OCD",
        "309.81": "PTSD"
    }

# Define severity adjustments (same as in app.py)
def define_severity_adjustments():
    return {
        "severe": 1.0,
        "moderate": 0.75,
        "mild": 0.5,
        "none": 0.0
    }

def create_decision_tree():
    questions = load_questions()
    disorders = define_disorders()
    severity_adjustments = define_severity_adjustments()
    
    # Create a new Graphviz digraph
    dot = graphviz.Digraph(comment='DSM-5-TR Decision Tree')
    dot.attr(rankdir='LR')  # Left to right layout
    dot.attr('node', shape='box', style='rounded,filled', fillcolor='lightblue')
    
    # Count symptoms per disorder for threshold calculation
    symptoms_per_disorder = defaultdict(int)
    for q in questions:
        for dsm_code in q.get("dsm_codes", []):
            symptoms_per_disorder[dsm_code] += 1
            
    # Calculate threshold (70% of symptoms required)
    threshold_per_disorder = {code: math.ceil(count * 0.7) for code, count in symptoms_per_disorder.items()}
    
    # Track which questions have dependencies and which are entry points
    has_dependency = set()
    for q in questions:
        if "dependency" in q:
            has_dependency.add(q["symptom"])
        elif "dependencies" in q:
            has_dependency.add(q["symptom"])

    # Add nodes for disorders with threshold information
    for code, name in disorders.items():
        threshold = threshold_per_disorder.get(code, 0)
        total = symptoms_per_disorder.get(code, 0)
        dot.node(f"disorder_{code}", 
                f"{name}\n({code})\nRequired: {threshold}/{total} symptoms\nMinimum certainty: 40%", 
                shape='box', style='filled', fillcolor='lightsalmon')
    
    # Add nodes for questions (using symptom names instead of full questions)
    for q in questions:
        node_id = f"q_{q['symptom']}"
        symptom_text = q['symptom'].replace('_', ' ').title()
        binary = q.get('binary', False)
        if binary:
            dot.node(node_id, f"{symptom_text}\n(Yes/No)")
        else:
            dot.node(node_id, f"{symptom_text}\n(Severity rated)")
        
        # Add edges for dependencies
        if "dependency" in q:
            dot.edge(f"q_{q['dependency']}", node_id, label="Yes")
        elif "dependencies" in q:
            for dep in q["dependencies"]:
                dot.edge(f"q_{dep}", node_id, label="Yes")
    
    # Add simplified edges from questions to disorders with severity information
    for q in questions:
        node_id = f"q_{q['symptom']}"
        binary = q.get('binary', False)
        
        for dsm_code in q.get("dsm_codes", []):
            if binary:
                # For binary questions, just show regular connection
                dot.edge(node_id, f"disorder_{dsm_code}", style="dashed", color="gray", label="Yes")
            else:
                # For severity questions, use a single edge with a label explaining the scaling
                dot.edge(node_id, f"disorder_{dsm_code}", 
                        style="dashed", 
                        color="purple", 
                        label="Severity scaling:\nSevere: 100%\nModerate: 75%\nMild: 50%")
    
    # Find entry point questions (those without dependencies)
    entry_points = []
    for q in questions:
        if q["symptom"] not in has_dependency and not ("dependency" in q or "dependencies" in q):
            entry_points.append(q["symptom"])
    
    # Add a start node and connect to entry points
    if entry_points:
        dot.node("start", "Start Assessment", shape="oval", style="filled", fillcolor="lightgreen")
        for entry in entry_points:
            dot.edge("start", f"q_{entry}")
    
    # Add a global legend explaining severity impact
    with dot.subgraph(name="cluster_legend") as legend:
        legend.attr(label="Severity Impact Legend", style="filled", fillcolor="white")
        legend.node("legend_severe", "Severe: 100% impact", shape="box", style="filled", fillcolor="#FFCCCC")
        legend.node("legend_moderate", "Moderate: 75% impact", shape="box", style="filled", fillcolor="#FFEEBB")
        legend.node("legend_mild", "Mild: 50% impact", shape="box", style="filled", fillcolor="#FFFFCC")
        
        # Connect legend nodes invisibly to create a vertical layout
        legend.edge("legend_severe", "legend_moderate", style="invis")
        legend.edge("legend_moderate", "legend_mild", style="invis")
    
    return dot

def create_disorder_specific_tree(target_disorder):
    """Create a decision tree focused on a single disorder"""
    questions = load_questions()
    disorders = define_disorders()
    severity_adjustments = define_severity_adjustments()
    
    if target_disorder not in disorders:
        raise ValueError(f"Unknown disorder: {target_disorder}")
    
    disorder_name = disorders[target_disorder]
    
    # Create a new Graphviz digraph
    dot = graphviz.Digraph(comment=f'{disorder_name} Decision Tree')
    dot.attr(rankdir='TB')  # Top to bottom layout
    dot.attr('node', shape='box', style='rounded,filled', fillcolor='lightblue')
    
    # Count symptoms for threshold calculation
    symptom_count = sum(1 for q in questions if target_disorder in q.get("dsm_codes", []))
    threshold = math.ceil(symptom_count * 0.7)
    
    # Add disorder node
    dot.node(f"disorder", 
            f"{disorder_name}\n({target_disorder})\nRequired: {threshold}/{symptom_count} symptoms\nMinimum certainty: 40%", 
            shape='box', style='filled', fillcolor='lightsalmon')
    
    # Track dependencies
    has_dependency = set()
    for q in questions:
        if "dependency" in q and target_disorder in q.get("dsm_codes", []):
            has_dependency.add(q["symptom"])
        elif "dependencies" in q and target_disorder in q.get("dsm_codes", []):
            has_dependency.add(q["symptom"])
    
    # Add question nodes and edges
    relevant_questions = [q for q in questions if target_disorder in q.get("dsm_codes", [])]
    for q in relevant_questions:
        node_id = f"q_{q['symptom']}"
        symptom_text = q['symptom'].replace('_', ' ').title()
        binary = q.get('binary', False)
        
        if binary:
            dot.node(node_id, f"{symptom_text}\n(Yes/No)")
            dot.edge(node_id, "disorder", label="Yes", style="dashed")
        else:
            dot.node(node_id, f"{symptom_text}\n(Severity rated)")
            
            # Create a gradient label for severity
            dot.edge(node_id, "disorder", 
                   label="Severity Impact:\nSevere: 100%\nModerate: 75%\nMild: 50%",
                   color="purple", style="dashed")
        
        # Add dependency edges
        if "dependency" in q:
            dep = q["dependency"]
            # Only add edge if dependency is also relevant to this disorder
            if any(target_disorder in dq.get("dsm_codes", []) for dq in questions if dq["symptom"] == dep):
                dot.edge(f"q_{dep}", node_id, label="Yes")
        elif "dependencies" in q:
            for dep in q["dependencies"]:
                if any(target_disorder in dq.get("dsm_codes", []) for dq in questions if dq["symptom"] == dep):
                    dot.edge(f"q_{dep}", node_id, label="Yes")
    
    # Add start node connecting to entry points
    entry_points = [q["symptom"] for q in relevant_questions 
                   if q["symptom"] not in has_dependency and not ("dependency" in q or "dependencies" in q)]
    
    if entry_points:
        dot.node("start", "Start Assessment", shape="oval", style="filled", fillcolor="lightgreen")
        for entry in entry_points:
            dot.edge("start", f"q_{entry}")
    
    return dot

def create_simplified_tree():
    """Create a simplified version of the decision tree with fewer connections"""
    questions = load_questions()
    disorders = define_disorders()
    severity_adjustments = define_severity_adjustments()
    
    # Count symptoms per disorder for threshold calculation
    symptoms_per_disorder = defaultdict(int)
    for q in questions:
        for dsm_code in q.get("dsm_codes", []):
            symptoms_per_disorder[dsm_code] += 1
            
    # Calculate threshold (70% of symptoms required)
    threshold_per_disorder = {code: math.ceil(count * 0.7) for code, count in symptoms_per_disorder.items()}
    
    dot = graphviz.Digraph(comment='Simplified DSM-5-TR Decision Tree')
    dot.attr(rankdir='TB')  # Top to bottom layout
    dot.attr('node', shape='box', style='rounded,filled', fillcolor='lightblue')
    
    # Group by disorder
    for code, name in disorders.items():
        # Create a subgraph for each disorder
        threshold = threshold_per_disorder.get(code, 0)
        total = symptoms_per_disorder.get(code, 0)
        
        with dot.subgraph(name=f"cluster_{code}") as c:
            c.attr(label=f"{name} ({code})\nRequired: {threshold}/{total} symptoms", 
                  style='filled', fillcolor='lightyellow')
            
            # Add severity legend to each disorder cluster
            c.node(f"severity_legend_{code}", 
                   "Severity Impact:\nSevere: 100%\nModerate: 75%\nMild: 50%",
                   shape="note", style="filled", fillcolor="lightcyan")
            
            # Add relevant questions
            for q in questions:
                if code in q.get("dsm_codes", []):
                    node_id = f"{code}_{q['symptom']}"
                    symptom_text = q['symptom'].replace('_', ' ').title()
                    
                    if q.get('binary', False):
                        c.node(node_id, f"{symptom_text}\n(Yes/No)")
                    else:
                        c.node(node_id, f"{symptom_text}\n(Severity rated)")
                    
                    # Add dependency edges within the same disorder
                    if "dependency" in q:
                        dep = q["dependency"]
                        dep_node = f"{code}_{dep}"
                        if any(code in dq.get("dsm_codes", []) for dq in questions if dq["symptom"] == dep):
                            c.edge(dep_node, node_id, label="Yes")
    
    return dot

def main():
    dot = create_decision_tree()
    
    output_dir = "renders"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "decision_tree")
    
    try:
        # Try to render using different formats
        dot.render(output_path, format='png', cleanup=True)
        print(f"Decision tree generated at {output_path}.png")
        
        # Also generate SVG for better web viewing
        dot.render(output_path, format='svg', cleanup=True)
        print(f"Decision tree generated at {output_path}.svg")
        
        # Generate the simplified tree
        simplified_dot = create_simplified_tree()
        simplified_output = os.path.join(output_dir, "decision_tree_simple")
        simplified_dot.render(simplified_output, format='png', cleanup=True)
        simplified_dot.render(simplified_output, format='svg', cleanup=True)
        print(f"Simplified tree generated at {simplified_output}.png/svg")
        
        # Generate individual disorder-specific trees
        disorders = define_disorders()
        for dsm_code in disorders:
            disorder_dot = create_disorder_specific_tree(dsm_code)
            disorder_output = os.path.join(output_dir, f"decision_tree_{dsm_code}")
            disorder_dot.render(disorder_output, format='png', cleanup=True)
            disorder_dot.render(disorder_output, format='svg', cleanup=True)
            print(f"Disorder tree for {dsm_code} generated at {disorder_output}.png/svg")
    
    except Exception as e:
        print(f"Error rendering decision tree: {e}")
        print("Attempting to create disorder-specific visualizations...")
        disorders = define_disorders()
        for dsm_code in disorders:
            try:
                disorder_dot = create_disorder_specific_tree(dsm_code)
                disorder_output = os.path.join(output_dir, f"decision_tree_{dsm_code}")
                disorder_dot.render(disorder_output, format='png', cleanup=True)
                disorder_dot.render(disorder_output, format='svg', cleanup=True)
                print(f"Disorder tree for {dsm_code} generated at {disorder_output}.png/svg")
            except Exception as inner_e:
                print(f"Error generating visualization for {dsm_code}: {inner_e}")

if __name__ == "__main__":
    main()
