                            
  
                                                                  
                                                                   
                                          
  
                                                 
  
                                                                      
                                                                    
                                                                           
                                                                      
                                 

#include "util.h"

#include <string>

namespace hanabi_learning_env {

char ColorIndexToChar(int color) {
  if (color >= 0 && color <= kMaxNumColors) {
    return "RYGWB"[color];
  } else {
    return 'X';
  }
}

char RankIndexToChar(int rank) {
  if (rank >= 0 && rank <= kMaxNumRanks) {
    return "12345"[rank];
  } else {
    return 'X';
  }
}

template <>
int ParameterValue<int>(
    const std::unordered_map<std::string, std::string>& params,
    const std::string& key, int default_value) {
  auto iter = params.find(key);
  if (iter == params.end()) {
    return default_value;
  }

  return std::stoi(iter->second);
}

template <>
std::string ParameterValue<std::string>(
    const std::unordered_map<std::string, std::string>& params,
    const std::string& key, std::string default_value) {
  auto iter = params.find(key);
  if (iter == params.end()) {
    return default_value;
  }

  return iter->second;
}

template <>
double ParameterValue<double>(
    const std::unordered_map<std::string, std::string>& params,
    const std::string& key, double default_value) {
  auto iter = params.find(key);
  if (iter == params.end()) {
    return default_value;
  }

  return std::stod(iter->second);
}

template <>
bool ParameterValue<bool>(
    const std::unordered_map<std::string, std::string>& params,
    const std::string& key, bool default_value) {
  auto iter = params.find(key);
  if (iter == params.end()) {
    return default_value;
  }

  return (iter->second == "1" || iter->second == "true" ||
                  iter->second == "True"
              ? true
              : false);
}

}                                  
