{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://seu-dominio.com/schemas/instagram-ads-formato.schema.json",
  "title": "Esquema de Anúncios Instagram por Formato (2025)",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "formato": {
      "type": "string",
      "enum": ["Reels", "Stories", "Feed"]
    },
    "contexto_uso": {
      "type": "string",
      "enum": ["organico", "anuncio_pago"]
    },
    "tipo_conteudo": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "midia": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "tipo": {
              "type": "string",
              "enum": ["video", "imagem", "carrossel", "foto_sequencial"]
            },
            "duracao_segundos": {
              "type": ["number", "null"],
              "minimum": 0
            },
            "num_elementos": {
              "type": "number",
              "minimum": 1
            },
            "aspect_ratio": {
              "type": "string",
              "enum": ["9:16", "1:1", "4:5", "1.91:1", "16:9"]
            },
            "tem_audio": {
              "type": "boolean"
            },
            "tipo_audio": {
              "type": "string",
              "enum": [
                "musica_trending",
                "voz_off",
                "sem_audio",
                "efeitos_sonoros",
                "audio_original",
                "musica_licenciada_meta"
              ]
            },
            "especificacoes_tecnicas": {
              "type": "object",
              "additionalProperties": false,
              "properties": {
                "tamanho_max_mb": { "type": "number", "minimum": 1 },
                "resolucao_min": { "type": "string" },
                "formatos_aceitos": {
                  "type": "array",
                  "items": { "type": "string" },
                  "minItems": 1
                }
              },
              "required": ["tamanho_max_mb", "resolucao_min", "formatos_aceitos"]
            }
          },
          "required": ["tipo", "aspect_ratio", "tem_audio", "tipo_audio", "especificacoes_tecnicas"]
        },
        "copy": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "estrutura_narrativa": {
              "type": "string",
              "enum": ["gancho-desenvolvimento-cta", "problema-solucao", "storytelling", "lista", "tutorial", "antes-depois"]
            },
            "texto_sobreposto": {
              "type": "object",
              "additionalProperties": false,
              "properties": {
                "tem": { "type": "boolean" },
                "posicao": { "type": "string", "enum": ["centro", "topo", "rodape", "lateral"] },
                "limite_caracteres": { "type": "number", "minimum": 1 }
              },
              "required": ["tem"]
            },
            "legenda": {
              "type": "object",
              "additionalProperties": false,
              "properties": {
                "tem": { "type": "boolean" },
                "limite_caracteres": { "type": "number", "minimum": 0 },
                "estrutura": { "type": "string" },
                "pre_header_visivel_primeiros_caracteres": { "type": "number", "minimum": 0 }
              },
              "required": ["tem", "limite_caracteres"]
            },
            "hashtags": {
              "type": "object",
              "additionalProperties": false,
              "properties": {
                "quantidade_recomendada": { "type": "number", "minimum": 0, "maximum": 30 },
                "posicionamento": { "type": "string", "enum": ["fim_legenda", "primeiro_comentario", "inline"] }
              },
              "required": ["quantidade_recomendada", "posicionamento"]
            }
          },
          "required": ["estrutura_narrativa", "texto_sobreposto", "legenda", "hashtags"]
        },
        "interatividade": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "elementos_interativos": {
              "type": "array",
              "items": {
                "type": "string",
                "enum": ["poll", "quiz", "countdown", "sticker_pergunta", "slider_emoji", "sticker_produto", "nenhum"]
              },
              "uniqueItems": true
            },
            "cta_organico": {
              "type": ["string", "null"],
              "enum": [null, "link_na_bio", "comente_para_receber", "salve_este_post", "compartilhe_com_amigo", "marque_alguem"]
            },
            "cta_pago": {
              "type": ["string", "null"],
              "minLength": 2,
              "maxLength": 50
            },
            "shopping_habilitado": { "type": "boolean" },
            "produtos_taggeados": {
              "type": "array",
              "items": { "type": "string", "minLength": 1 },
              "uniqueItems": true
            },
            "branded_content_tag": { "type": "boolean" },
            "parceiro_branded_content": { "type": ["string", "null"] },
            "link_direto": { "type": "boolean" },
            "link_direto_url": {
              "type": ["string", "null"],
              "format": "uri"
            }
          },
          "required": ["shopping_habilitado", "branded_content_tag", "link_direto"]
        }
      },
      "required": ["midia", "copy", "interatividade"]
    },
    "estrategia": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "etapa_funil": { "type": "string", "enum": ["topo", "meio", "fundo"] },
        "objetivo_campanha": {
          "type": "string",
          "enum": ["reach", "video_views", "engagement", "traffic", "leads", "sales"]
        },
        "metricas_principais": {
          "type": "array",
          "items": { "type": "string" },
          "minItems": 1
        },
        "publico_alvo": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "temperatura": { "type": "string", "enum": ["frio", "morno", "quente"] },
            "comportamento_esperado": { "type": "string" }
          },
          "required": ["temperatura"]
        },
        "setor_mercado": {
          "type": "string",
          "enum": ["geral", "saude_bem_estar", "ecommerce_varejo", "servicos_b2b"]
        }
      },
      "required": ["etapa_funil", "objetivo_campanha", "metricas_principais", "setor_mercado"]
    },
    "validacoes": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "politicas_aplicaveis": { "type": "array", "items": { "type": "string" } },
        "restricoes_setor": { "type": "array", "items": { "type": "string" } }
      }
    }
  },
  "required": ["formato", "contexto_uso", "tipo_conteudo", "estrategia"],

  "allOf": [
    /* ====== REELS ====== */
    {
      "if": { "properties": { "formato": { "const": "Reels" } } },
      "then": {
        "properties": {
          "tipo_conteudo": {
            "properties": {
              "midia": {
                "properties": {
                  "tipo": { "enum": ["video", "foto_sequencial"] },
                  "aspect_ratio": { "const": "9:16" }
                }
              },
              "copy": {
                "properties": {
                  "legenda": {
                    "properties": {
                      "tem": { "const": true },
                      "limite_caracteres": { "maximum": 2200 },
                      "pre_header_visivel_primeiros_caracteres": { "const": 125 }
                    }
                  },
                  "texto_sobreposto": {
                    "properties": {
                      "limite_caracteres": { "maximum": 40 }
                    }
                  }
                }
              }
            }
          }
        }
      }
    },

    /* Reels - duração por contexto */
    {
      "if": {
        "properties": {
          "formato": { "const": "Reels" },
          "contexto_uso": { "const": "organico" },
          "tipo_conteudo": {
            "properties": { "midia": { "properties": { "tipo": { "const": "video" } } } }
          }
        }
      },
      "then": {
        "properties": {
          "tipo_conteudo": {
            "properties": { "midia": { "properties": { "duracao_segundos": { "maximum": 180, "exclusiveMinimum": true } } } }
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "formato": { "const": "Reels" },
          "contexto_uso": { "const": "anuncio_pago" },
          "tipo_conteudo": {
            "properties": { "midia": { "properties": { "tipo": { "const": "video" } } } }
          }
        }
      },
      "then": {
        "properties": {
          "tipo_conteudo": {
            "properties": { "midia": { "properties": { "duracao_segundos": { "maximum": 900, "exclusiveMinimum": true } } } }
          }
        }
      }
    },

    /* ====== STORIES ====== */
    {
      "if": { "properties": { "formato": { "const": "Stories" } } },
      "then": {
        "properties": {
          "tipo_conteudo": {
            "properties": {
              "midia": {
                "properties": {
                  "tipo": { "enum": ["video", "imagem"] },
                  "aspect_ratio": { "const": "9:16" }
                }
              },
              "copy": {
                "properties": {
                  "legenda": { "properties": { "tem": { "const": false } } },
                  "texto_sobreposto": {
                    "properties": { "tem": { "const": true } }
                  }
                }
              },
              "interatividade": {
                "properties": {
                  "link_direto": { "const": true }
                }
              }
            }
          }
        }
      }
    },

    /* Stories orgânico: exigir ao menos 1 elemento interativo */
    {
      "if": {
        "properties": {
          "formato": { "const": "Stories" },
          "contexto_uso": { "const": "organico" }
        }
      },
      "then": {
        "properties": {
          "tipo_conteudo": {
            "properties": {
              "interatividade": {
                "properties": {
                  "elementos_interativos": { "minItems": 1 }
                },
                "required": ["elementos_interativos"]
              }
            }
          }
        }
      }
    },

    /* Stories Ads - duração máxima de vídeo (60 min) */
    {
      "if": {
        "properties": {
          "formato": { "const": "Stories" },
          "contexto_uso": { "const": "anuncio_pago" },
          "tipo_conteudo": {
            "properties": { "midia": { "properties": { "tipo": { "const": "video" } } } }
          }
        }
      },
      "then": {
        "properties": {
          "tipo_conteudo": {
            "properties": { "midia": { "properties": { "duracao_segundos": { "maximum": 3600 } } } }
          }
        }
      }
    },

    /* ====== FEED ====== */
    {
      "if": { "properties": { "formato": { "const": "Feed" } } },
      "then": {
        "properties": {
          "tipo_conteudo": {
            "properties": {
              "midia": {
                "properties": {
                  "tipo": { "enum": ["imagem", "carrossel", "video"] },
                  "aspect_ratio": { "enum": ["1:1", "4:5", "1.91:1", "16:9"] }
                }
              },
              "copy": {
                "properties": {
                  "legenda": {
                    "properties": {
                      "tem": { "const": true },
                      "limite_caracteres": { "maximum": 2200 },
                      "pre_header_visivel_primeiros_caracteres": { "const": 125 }
                    }
                  }
                }
              }
            }
          }
        }
      }
    },

    /* Feed carrossel: 2–20 (orgânico) / 2–10 (ads) */
    {
      "if": {
        "properties": {
          "formato": { "const": "Feed" },
          "tipo_conteudo": {
            "properties": { "midia": { "properties": { "tipo": { "const": "carrossel" } } } }
          },
          "contexto_uso": { "const": "organico" }
        }
      },
      "then": {
        "properties": {
          "tipo_conteudo": {
            "properties": { "midia": { "properties": { "num_elementos": { "minimum": 2, "maximum": 20 } } } }
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "formato": { "const": "Feed" },
          "tipo_conteudo": {
            "properties": { "midia": { "properties": { "tipo": { "const": "carrossel" } } } }
          },
          "contexto_uso": { "const": "anuncio_pago" }
        }
      },
      "then": {
        "properties": {
          "tipo_conteudo": {
            "properties": { "midia": { "properties": { "num_elementos": { "minimum": 2, "maximum": 10 } } } }
          }
        }
      }
    },

    /* ====== REGRAS GLOBAIS ====== */

    /* Ads: bloquear musica_trending */
    {
      "if": { "properties": { "contexto_uso": { "const": "anuncio_pago" } } },
      "then": {
        "properties": {
          "tipo_conteudo": {
            "properties": {
              "midia": {
                "not": {
                  "properties": { "tipo_audio": { "const": "musica_trending" } },
                  "required": ["tipo_audio"]
                }
              },
              "interatividade": {
                "properties": {
                  "cta_pago": { "type": "string", "minLength": 2 }
                },
                "required": ["cta_pago"]
              }
            }
          }
        }
      }
    },

    /* Orgânico: cta_pago deve ser null e cta_organico permitido */
    {
      "if": { "properties": { "contexto_uso": { "const": "organico" } } },
      "then": {
        "properties": {
          "tipo_conteudo": {
            "properties": {
              "interatividade": {
                "properties": { "cta_pago": { "type": "null" } }
              }
            }
          }
        }
      }
    },

    /* Shopping: limites por formato */
    {
      "if": {
        "properties": {
          "tipo_conteudo": {
            "properties": {
              "interatividade": { "properties": { "shopping_habilitado": { "const": true } } }
            }
          }
        }
      },
      "then": {
        "allOf": [
          {
            "if": { "properties": { "formato": { "enum": ["Reels", "Feed"] } } },
            "then": {
              "properties": {
                "tipo_conteudo": {
                  "properties": {
                    "interatividade": {
                      "properties": {
                        "produtos_taggeados": { "maxItems": 20 }
                      }
                    }
                  }
                }
              }
            }
          },
          {
            "if": { "properties": { "formato": { "const": "Stories" } } } ,
            "then": {
              "properties": {
                "tipo_conteudo": {
                  "properties": {
                    "interatividade": {
                      "properties": { "produtos_taggeados": { "maxItems": 5 } }
                    }
                  }
                }
              }
            }
          }
        ]
      }
    },

    /* Branded content: exigir parceiro */
    {
      "if": {
        "properties": {
          "tipo_conteudo": {
            "properties": {
              "interatividade": { "properties": { "branded_content_tag": { "const": true } } }
            }
          }
        }
      },
      "then": {
        "properties": {
          "tipo_conteudo": {
            "properties": {
              "interatividade": {
                "properties": { "parceiro_branded_content": { "type": "string", "minLength": 2 } },
                "required": ["parceiro_branded_content"]
              }
            }
          }
        }
      }
    },

    /* Saúde & Bem-estar: bloquear 'antes-depois' */
    {
      "if": { "properties": { "estrategia": { "properties": { "setor_mercado": { "const": "saude_bem_estar" } } } } },
      "then": {
        "properties": {
          "tipo_conteudo": {
            "properties": {
              "copy": {
                "not": {
                  "properties": { "estrutura_narrativa": { "const": "antes-depois" } },
                  "required": ["estrutura_narrativa"]
                }
              }
            }
          }
        }
      }
    }
  ]
}
