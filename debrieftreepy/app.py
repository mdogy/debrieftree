
import streamlit as st
import numpy as np
import pandas as pd
from pathlib import Path
from loguru import logger
import yaml


LOGGER_FILE = "debug.log"
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
    logger.debug("current_path: {current_path}")
    assert all(one_id in list(data_loaded.iloc[:,0]) for one_id in current_path)
    
    for _ in range(MAXLOOP):
        current_node = current_path[-1]
        logger.debug(f"current_node: {current_node}")
        text_input = None
        node_row = data_loaded[data_loaded["nodeID"] == current_node].iloc[0]
        logger.debug(f"node_row: {node_row}")
        node_type, node_text = node_row["nodeType"], node_row["nodeText"]
        logger.debug(f"node_type: {node_type}")
        logger.debug(f"node_text: {node_text}")
        logger.debug(f"type(node_type): {type(node_type)}")
        select_children = (data_loaded["parentID"] == current_node)
        children_rows = data_loaded[select_children]
        logger.debug(f"children_rows: {children_rows}")
        
        # Remove empty values
        node_dict = {key:value 
                        for key, value in node_row.to_dict().items()
                        if str(value) not in ["", np.nan ,".nan", "nan", float("nan")]}
        logger.debug(f"node_dict: {node_dict}")
        # Remove keys that are not needed for the report
        for key in ["nodeType", "nodeID", "parentID", "option"]:
            if key in node_dict:
                del node_dict[key]
        logger.debug(f"node_dict: {node_dict}")   
        logger.debug(f"node_type: {node_type}")

        
        if node_type == 'leaf':
            # Dump the node_dict to a yaml string as report
            logger.debug(f"Branch Leaf")
            
            formatted_node = yaml.dump(node_dict,
                                      default_flow_style=False)
            collected_info.append(formatted_node)
            return formatted_node
        elif node_type == "selectbox":
            logger.debug(f"Branch Selectbox")
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
            next_children_rows = children_rows['nodeID']
            logger.debug(f"next_children_rows: {next_children_rows}")
            next_node = next_children_rows.values[0]
            logger.debug(f"next_node: {next_node}")
            current_path.append(next_node)
            logger.debug(f"current_path: {current_path}")
        else: 
            question_type = data_loaded.loc[current_node,"nodeType" ]
            Exception(f"Question type: {question_type} not implemented")
        
        # Update the report   
        if node_dict:
            formatted_node = yaml.dump(node_dict,
                                default_flow_style=False)
            collected_info.append(formatted_node)
            
def check_df(df, ROOTNODEID):
    check_passed = True
    if 'nodeID' not in df.columns:
        logger.error("nodeID column is missing")
        check_passed = False
        return check_passed
    
    if 'nodeType' not in df.columns:
        logger.error("nodeType column is missing")
        check_passed = False
        return check_passed
    
    if 'nodeText' not in df.columns:
        logger.error("nodeText column is missing")
        check_passed = False
        return check_passed
    
    if 'parentID' not in df.columns:
        logger.error("parentID column is missing")
        check_passed = False
        return check_passed
    
    # Check that the parentID is in the nodeID
    for index, row in df.iterrows():
        if row['nodeID']!= ROOTNODEID:
            if row['parentID'] not in df['nodeID'].to_list():
                logger.error(f"parentID: {row['parentID']} is not in the nodeID")
                check_passed = False
        
    # Check that the nodeID is unique
    if len(df['nodeID'].unique()) != len(df['nodeID']):
        logger.error("nodeID is not unique")
        check_passed = False
        return check_passed
    
    # Check that the if the nodeType is textarea, then there is only one child
    for index, row in df.iterrows():
        if row['nodeType'] == 'textarea':
            if len(df[df['parentID'] == row['nodeID']]) > 1:
                logger.error(f"nodeID: {row['nodeID']} has more than one child")
                check_passed = False
    
    # Check that if the nodeType is leaf, then there are no children
    for index, row in df.iterrows():
        if row['nodeType'] == 'leaf':
            if len(df[df['parentID'] == row['nodeID']]) > 0:
                logger.error(f"nodeID: {row['nodeID']} has children")
                check_passed = False
    
    # Check that if the nodeType is selectbox, then there are children
    for index, row in df.iterrows():
        if row['nodeType'] == 'selectbox':
            if len(df[df['parentID'] == row['nodeID']]) == 0:
                logger.error(f"nodeID: {row['nodeID']} has no children")
                check_passed = False
    
    # Check that if the nodeID has no children, then the nodeType is leaf
    for index, row in df.iterrows():
        if len(df[df['parentID'] == row['nodeID']]) == 0:
            if row['nodeType'] != 'leaf':
                logger.error(f"nodeID: {row['nodeID']} has no children but nodeType is not leaf")
                check_passed = False
    
   
    return check_passed 
                
def main():

    DATAPATH = Path("data/raw")
    FNAME = "SampleFormatTreeData.csv"
    FNAME = "DecisionTrees3.csv"

    fid = open(LOGGER_FILE, "a")
    logger.add(fid,
                format="{time} {level} {message}",
                level="DEBUG")

    df = pd.read_csv(DATAPATH / FNAME)
    
    ROOTNODEID = min(df['nodeID'].to_list())
     
    if not check_df(df, ROOTNODEID):
        raise Exception("Dataframe check failed")
    

    if 'path' not in st.session_state:
        st.session_state.path = []
    
    st.session_state.path.clear()
    st.session_state.path.append(ROOTNODEID)
    
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
            logger.info(f"Information Collected: {st.session_state.collected_info}")
    else:
        logger.info(f"Still Collecting Information")
    
    return
  
    
if __name__ == "__main__":
    main()
    



