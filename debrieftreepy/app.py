
import streamlit as st
from pydantic import BaseModel, ValidationError
from typing import Dict, List, Union, Optional
import typer
import numpy as np
import pandas as pd
from pathlib import Path
from loguru import logger
from tqdm import tqdm
import yaml


MAXLOOP = 1000

def display_question(data_loaded, 
                     current_path, 
                     collected_info):
    """
    Recursively display questions based on the tree and user's path.
    
    Args:
        tree (Dict[str, Dict]): The current level of the decision tree.
        path (List[str]): The path of questions and answers chosen by the user.
        depth (int): The current depth in the tree to manage unique keys.
    
    Returns:
        Optional[str]: The final answer based on the user's selections, if any.
    """

  
    # Base case: if the tree is a string, return it as the final answer
    assert len(current_path) > 0
    assert all(one_id in list(data_loaded.iloc[:,0]) for one_id in current_path)
 
    for _ in range(MAXLOOP):
        current_node = current_path[-1]
        print("current_node: ", current_node)
        text_input = None
        node_row = data_loaded.iloc[current_node,:]
        node_type, node_text = node_row["nodeType"], node_row["nodeText"]
        select_children = data_loaded["parentID"] == current_node
        children_rows = data_loaded[select_children]
        # Remove empty values
        node_dict = {key:value 
                        for key, value in node_row.to_dict().items()
                        if str(value) not in ["", np.nan ,".nan", "nan", float("nan")]}
        # Remove keys that are not needed for the report
        for key in ["nodeType", "nodeID", "parentID", "option"]:
            if key in node_dict:
                del node_dict[key]
                
        # Dump the node_dict to a yaml string as report
        if node_type == "leaf":
            formatted_node = yaml.dump(node_dict,
                                      default_flow_style=False)
            collected_info.append(formatted_node)
            return formatted_node
        elif node_type == "selectbox":
          
            option_list = list(children_rows["option"])
            if len(option_list) == 0:
              Exception(f"Node {current_node} has no options")
            options = ["Select an option"] + option_list
            # To get the ids of the children nodes by "option"
            option2id = dict([(option, nodeID) for option, nodeID 
                              in zip(options[1:], children_rows["nodeID"])])
            selected_option = st.selectbox(
                label=node_text,
                options=options,
                format_func=lambda x: x if x == "Select an option" else x,
                key=f"{current_node}"
            )
            # If nothing is selected, then leave the function
            if selected_option == "Select an option":
                return None
            # Lookup next node based on the selected option
            current_path.append(option2id[selected_option])
            # Add the selected option to the node_dict for the report
            node_dict["selected_option"] = selected_option
        elif node_type == "textarea":
            # This node just collects text input for text report
            text_input = st.text_area(node_text)
            if text_input == "":
                return None
            node_dict["response"] = text_input
            # There can be only one child node for a text area
            next_node = children_rows['nodeID'].values[0]
            current_path.append(next_node)
        else: 
            question_type = data_loaded.loc[current_node,"nodeType" ]
            Exception(f"Question type: {question_type} not implemented")
        
        # Update the report   
        if node_dict:
            formatted_node = yaml.dump(node_dict,
                                default_flow_style=False)
            collected_info.append(formatted_node)                      
def main():
    
  DATAPATH = Path("data/raw")
  FNAME = "SampleFormatTreeData.csv"
  df = pd.read_csv(DATAPATH / FNAME)
  ROOTNODEID = 0
  
  if 'path' not in st.session_state:
      st.session_state.path = []
  
  st.session_state.path.clear()
  st.session_state.path.append(0)
  
  if 'collected_info' not in st.session_state:
      st.session_state.collected_info = []
      
  st.session_state.collected_info.clear()
  
  final_answer = display_question(df, 
                                  st.session_state.path,
                                  st.session_state.collected_info)

  if final_answer:  
    if st.session_state.collected_info:
      st.write("### Information Collected:")
      st.text('\n\n'.join(st.session_state.collected_info))
      print("Information Collected: ", st.session_state.collected_info)
  else:
    print("Still Collecting Information")
  
  return
  
    
if __name__ == "__main__":
    main()
    



