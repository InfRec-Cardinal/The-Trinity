                            
  
                                                                  
                                                                   
                                          
  
                                                 
  
                                                                      
                                                                    
                                                                           
                                                                      
                                 

#ifndef __UTIL_H__
#define __UTIL_H__

#include <cassert>
#include <cstdlib>
#include <string>
#include <unordered_map>

namespace hanabi_learning_env {

constexpr int kMaxNumColors = 5;
constexpr int kMaxNumRanks = 5;

                                                                     
char ColorIndexToChar(int color);
char RankIndexToChar(int rank);

                                                                         
                                                               
template <class T>
T ParameterValue(const std::unordered_map<std::string, std::string>& params,
                 const std::string& key, T default_value);

template <>
int ParameterValue(const std::unordered_map<std::string, std::string>& params,
                   const std::string& key, int default_value);
template <>
double ParameterValue(
    const std::unordered_map<std::string, std::string>& params,
    const std::string& key, double default_value);
template <>
std::string ParameterValue(
    const std::unordered_map<std::string, std::string>& params,
    const std::string& key, std::string default_value);
template <>
bool ParameterValue(const std::unordered_map<std::string, std::string>& params,
                    const std::string& key, bool default_value);

#if defined(NDEBUG)
#define REQUIRE(expr)                                                        \
  (expr ? (void)0                                                            \
        : (fprintf(stderr, "Input requirements failed at %s:%d in %s: %s\n", \
                   __FILE__, __LINE__, __func__, #expr),                     \
           std::abort()))
#else
#define REQUIRE(expr) assert(expr)
#endif

}                                  

#endif
